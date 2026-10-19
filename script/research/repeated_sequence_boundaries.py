"""Extend a repeated core using aligned, frame-by-frame cross-clip agreement.

These are clip-local correspondence boundaries, not verified separator or source
cut boundaries. Repeated advertisements can satisfy exactly the same criteria.
"""

import numpy as np

from repeated_visual_sequences import window_scores


def refine(features, candidate, fps=25, min_clips=3, max_rmse=15):
    occurrences = candidate["occurrences"]
    if len(occurrences) < min_clips or len({row["clip_index"] for row in occurrences}) != len(occurrences):
        return {"status": "unavailable", "reason": "Need one unambiguous occurrence per supporting clip"}
    reference = occurrences[0]
    reference_frames = features[reference["clip_index"]]
    middle = (reference["core_start_seconds"] + reference["core_end_seconds"]) / 2
    anchor = round((middle - 0.5) * fps)
    window = round(fps)
    template = reference_frames[anchor:anchor + window]
    if anchor < 0 or len(template) != window:
        return {"status": "unavailable", "reason": "Insufficient anchor context"}
    offsets, distances = [0], []
    for row in occurrences[1:]:
        frames = features[row["clip_index"]]
        lower = max(0, round((row["core_start_seconds"] - 1) * fps))
        upper = min(len(frames), round((row["core_end_seconds"] + 1) * fps))
        scores = window_scores(template, frames[lower:upper], window)
        if not scores.size or scores.min() > max_rmse:
            return {"status": "unavailable", "reason": "No reliable temporal alignment"}
        offset = lower + int(np.argmin(scores[0])) - anchor
        offsets.append(offset)
        distance = np.full(len(reference_frames), np.inf)
        first = max(0, -offset)
        last = min(len(reference_frames), len(frames) - offset)
        distance[first:last] = np.sqrt(np.mean(
            (reference_frames[first:last] - frames[first + offset:last + offset]) ** 2, axis=1
        )) * 255
        distances.append(distance)

    median = np.median(distances, axis=0)
    support = np.sum(np.asarray(distances) <= max_rmse, axis=0)
    valid = (median <= max_rmse) & (support >= min_clips - 1)
    left = right = anchor + window // 2
    if not valid[left]:
        return {"status": "unavailable", "reason": "Anchor does not have enough cross-clip support"}
    lower = max(0, *(-offset for offset in offsets))
    upper = min(len(features[row["clip_index"]]) - offset for row, offset in zip(occurrences, offsets))
    while left > lower and valid[left - 1]:
        left -= 1
    while right < upper and valid[right]:
        right += 1
    if right - left < window:
        return {"status": "unavailable", "reason": "Shared run is shorter than one second"}
    return {
        "status": "experimental", "classification": "unverified_shared_run",
        "needs_manual_review": True, "fps": fps,
        "occurrences": [
            {"clip_index": row["clip_index"], "sampled_start_frame": left + offset,
             "sampled_end_frame_exclusive": right + offset,
             "clip_start_seconds": (left + offset) / fps,
             "clip_end_seconds_exclusive": (right + offset) / fps}
            for row, offset in zip(occurrences, offsets)
        ],
        "duration_seconds": (right - left) / fps,
        "coordinate_system": "resampled_clip_timeline_starting_at_zero; not native video frame indices",
        "semantic_status": "Cannot distinguish a separator from a repeated advertisement",
        "source_mapping": "unverified; do not use these clip frames as original source frames",
    }
