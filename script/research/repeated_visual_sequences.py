"""Research only: discover repeated moving sequences across short clips.

No channel templates, reference boundaries, OCR, or automatic cut decisions.
Requires ffmpeg, ffprobe and NumPy. Times refer to the supplied clips only.
"""

import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np


def decode(path, sample_fps=5):
    metadata = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    duration = float(json.loads(metadata.stdout)["format"]["duration"])
    if not math.isfinite(duration) or not 0 < duration <= 120:
        raise ValueError("Use observation clips of at most 120 seconds; full-capture scanning is not implemented")
    pixels = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-an", "-sn", "-vf",
         f"fps={sample_fps}:start_time=0,scale=32:18", "-pix_fmt", "rgb24",
         "-fps_mode", "passthrough", "-f", "rawvideo", "pipe:1"],
        check=True, capture_output=True,
    ).stdout
    if len(pixels) % 1728:
        raise ValueError("Incomplete decoded frame")
    return np.frombuffer(pixels, dtype=np.uint8).reshape(-1, 1728).astype(np.float32) / 255


def require_25fps(path):
    """The local refinement pilot currently requires constant 25 fps excerpts."""
    metadata = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=avg_frame_rate,r_frame_rate", "-of", "json", str(path)],
        check=True, capture_output=True, text=True,
    )
    stream = json.loads(metadata.stdout)["streams"][0]
    if any(stream.get(key) != "25/1" for key in ["avg_frame_rate", "r_frame_rate"]):
        raise ValueError("Local boundary refinement currently requires constant 25 fps clips")


def window_scores(left, right, window):
    """Compare ordered windows, preserving spatial layout and temporal order."""
    left_count, right_count = len(left) - window + 1, len(right) - window + 1
    if left_count <= 0 or right_count <= 0:
        return np.empty((0, 0), dtype=np.float32)
    distance = np.maximum(
        0, np.mean(left * left, axis=1)[:, None] + np.mean(right * right, axis=1)[None, :]
        - 2 * (left @ right.T) / left.shape[1],
    )
    scores = np.zeros((left_count, right_count), dtype=np.float32)
    for shift in range(window):
        scores += distance[shift:shift + left_count, shift:shift + right_count]
    return np.sqrt(scores / window) * 255


def motion_scores(frames, window):
    count = len(frames) - window + 1
    if count <= 0:
        return np.empty(0)
    energy = np.mean(np.diff(frames, axis=0) ** 2, axis=1)
    return np.sqrt(np.convolve(energy, np.ones(window - 1) / (window - 1), mode="valid")) * 255


class Components:
    def __init__(self):
        self.parents = {}

    def root(self, node):
        self.parents.setdefault(node, node)
        if self.parents[node] != node:
            self.parents[node] = self.root(self.parents[node])
        return self.parents[node]

    def join(self, left, right):
        self.parents[self.root(left)] = self.root(right)


def discover(features, sample_fps=5, window_seconds=2, max_rmse=15, min_motion=2, min_clips=3):
    window = round(window_seconds * sample_fps)
    if window < 2 or min_clips < 2 or not 0 < min_motion or not 0 < max_rmse:
        raise ValueError("Invalid discovery settings")
    graph, edges = Components(), []
    motions = [motion_scores(frames, window) for frames in features]
    for left in range(len(features)):
        for right in range(left + 1, len(features)):
            scores = window_scores(features[left], features[right], window)
            if not scores.size:
                continue
            accepted = (scores <= max_rmse) & (motions[left][:, None] >= min_motion)
            accepted &= motions[right][None, :] >= min_motion
            for start_left, start_right in zip(*np.nonzero(accepted)):
                a, b = (left, int(start_left)), (right, int(start_right))
                graph.join(a, b)
                edges.append((a, b, float(scores[start_left, start_right])))

    # Merge overlapping candidate cores in the same clip, not disjoint occurrences.
    for clip in range(len(features)):
        nodes = sorted(node for node in graph.parents if node[0] == clip)
        for previous, following in zip(nodes, nodes[1:]):
            if following[1] - previous[1] <= window // 2:
                graph.join(previous, following)

    groups = {}
    for node in graph.parents:
        groups.setdefault(graph.root(node), []).append(node)
    candidates = []
    for root, nodes in groups.items():
        clips = sorted({node[0] for node in nodes})
        if len(clips) < min_clips:
            continue
        distances = [score for a, _b, score in edges if graph.root(a) == root]
        occurrences = []
        for clip in clips:
            starts = sorted(node[1] for node in nodes if node[0] == clip)
            runs = [[starts[0]]]
            for start in starts[1:]:
                if start - runs[-1][-1] > window // 2:
                    runs.append([])
                runs[-1].append(start)
            for run in runs:
                occurrences.append({"clip_index": clip, "core_start_seconds": run[0] / sample_fps,
                                    "core_end_seconds": (run[-1] + window) / sample_fps})
        candidates.append({"classification": "unverified_repeated_visual_sequence",
                           "supporting_clips": len(clips), "occurrences": occurrences,
                           "best_rmse": round(min(distances), 3),
                           "median_rmse": round(float(np.median(distances)), 3)})
    return sorted(candidates, key=lambda row: (-row["supporting_clips"], row["median_rmse"]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("clips", type=Path, nargs="+")
    parser.add_argument("--min-clips", type=int, default=3)
    parser.add_argument("--refine-local-boundaries", action="store_true")
    options = parser.parse_args(argv)
    paths = [path.resolve(strict=True) for path in options.clips]
    if len(set(paths)) != len(paths):
        raise ValueError("The same clip cannot count as independent support twice")
    features = [decode(path) for path in paths]
    report = {
        "format": "video_encoder.repeated_visual_sequence_research", "version": 1,
        "status": "experimental", "needs_manual_review": True,
        "settings": {"sample_fps": 5, "window_seconds": 2, "max_rgb_rmse": 15,
                     "min_motion_rmse": 2, "min_supporting_clips": options.min_clips},
        "clips": [str(path) for path in paths],
        "candidates": discover(features, min_clips=options.min_clips),
        "limitations": ["Repeated advertisements or programme sequences can also match",
                        "Intervals describe repeated cores, not separator or cut boundaries",
                        "Times are relative to clips, not original source frame numbers",
                        "No project is created or modified; audio is not analysed"],
    }
    if options.refine_local_boundaries:
        from repeated_sequence_boundaries import refine
        for path in paths:
            require_25fps(path)
        full_rate = [decode(path, sample_fps=25) for path in paths]
        report["local_boundary_experiment"] = [
            refine(full_rate, candidate, min_clips=options.min_clips) for candidate in report["candidates"]
        ]
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(1)
