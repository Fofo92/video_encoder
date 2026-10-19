"""Describe independent evidence around repeated motifs; never decide cuts."""

import subprocess
import numpy as np


def decode_audio(path):
    process = subprocess.run(
        ["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-map", "0:a:0?", "-vn",
         "-ac", "1", "-ar", "8000", "-af", "aresample=8000:first_pts=0", "-f", "f32le", "pipe:1"],
        capture_output=True,
    )
    if process.returncode:
        return None
    return np.frombuffer(process.stdout, dtype="<f4")


def spectral_fingerprint(audio):
    if audio is None or len(audio) < 256 or not np.isfinite(audio).all():
        return None
    if np.sqrt(np.mean(audio ** 2)) < 1e-5:
        return None
    windows = np.lib.stride_tricks.sliding_window_view(audio, 256)[::80]
    power = np.abs(np.fft.rfft(windows * np.hanning(256), axis=1)) ** 2
    edges = np.unique(np.round(np.geomspace(1, 129, 21)).astype(int))
    bands = np.stack([power[:, a:b].mean(axis=1) for a, b in zip(edges, edges[1:])], axis=1)
    bands = np.log(np.maximum(bands, 1e-12))
    bands -= bands.mean(axis=1, keepdims=True)
    return bands / np.maximum(np.linalg.norm(bands, axis=1, keepdims=True), 1e-9)


def audio_similarity(left, right):
    left, right = spectral_fingerprint(left), spectral_fingerprint(right)
    if left is None or right is None:
        return None
    comparisons = []
    for shift in range(-10, 11):
        begin = max(0, -shift)
        end = min(len(left), len(right) - shift)
        if end - begin >= 50:
            comparisons.append(float(np.mean(np.sum(left[begin:end] * right[begin + shift:end + shift], axis=1))))
    return max(comparisons) if comparisons else None


def border_description(frames):
    if frames.shape[1:] != (1728,):
        return None
    pixels = frames.reshape(-1, 18, 32, 3)
    pixels = pixels[pixels.mean(axis=(1, 2, 3)) > 0.025]
    if len(pixels) < 10:
        return None
    border = np.concatenate([pixels[:, 0], pixels[:, -1]], axis=1).mean(axis=2)
    return round(float(np.mean(border < 24 / 255)), 4)


def border_transition(frames, first, last, fps=25):
    before = border_description(frames[max(0, first - 2 * fps):max(0, first - round(0.4 * fps))])
    after = border_description(frames[last + round(0.4 * fps):last + 2 * fps])
    direction = "unresolved"
    if before is not None and after is not None:
        if before >= 0.95 and after <= 0.2:
            direction = "dark_borders_to_full_frame"
        elif before <= 0.2 and after >= 0.95:
            direction = "full_frame_to_dark_borders"
    return {"before_dark_border_fraction": before, "after_dark_border_fraction": after,
            "direction": direction}


def characterize(features, audios, refined):
    if refined.get("status") != "experimental":
        return {"status": "unavailable", "reason": "No aligned repeated run"}
    rows, sounds = [], []
    fps = refined["fps"]
    for occurrence in refined["occurrences"]:
        clip = occurrence["clip_index"]
        first, last = occurrence["sampled_start_frame"], occurrence["sampled_end_frame_exclusive"]
        rows.append(dict(clip_index=clip, **border_transition(features[clip], first, last, fps)))
        audio = audios[clip]
        sounds.append(None if audio is None else audio[round(first * 8000 / fps):round(last * 8000 / fps)])
    similarities = [audio_similarity(left, right) for i, left in enumerate(sounds) for right in sounds[i + 1:]]
    available = [value for value in similarities if value is not None]
    directions = {row["direction"] for row in rows}
    return {
        "status": "experimental", "needs_manual_review": True,
        "border_contexts": rows,
        "reciprocal_border_changes": {"dark_borders_to_full_frame", "full_frame_to_dark_borders"} <= directions,
        "audio_pairs_compared": len(available),
        "audio_similarity_median": round(float(np.median(available)), 4) if available else None,
        "audio_similarity_minimum": round(min(available), 4) if available else None,
        "semantic_status": "Evidence only; repeated advertisements can share the same audiovisual signature",
        "source_mapping": "unverified",
    }
