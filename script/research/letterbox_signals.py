"""Experimental format-change signals on sampled pixels, never ad decisions."""
import math
import numpy as np


def classify_frames(frames, batch_size=300):
    """Return -1 unknown, 0 full-frame, 1 bilateral letterbox.

    Both borders must support a band. Entirely dark frames stay unknown rather
    than becoming letterbox evidence. At low resolution, boundaries are coarse.
    """
    if (frames.ndim != 4 or frames.shape[-1] != 3 or min(frames.shape[1:3]) < 8
            or frames.dtype != np.uint8 or batch_size < 1):
        raise ValueError('Expected uint8 RGB observation frames of at least 8x8 pixels')
    height = frames.shape[1]
    labels = np.full(len(frames), -1, dtype=np.int8)
    for first in range(0, len(frames), batch_size):
        block = frames[first:first + batch_size].astype(np.float32)
        luma = block @ np.array([.2126, .7152, .0722], dtype=np.float32)
        dark_rows = (np.mean(luma <= 24, axis=2) >= .9) & (np.std(luma, axis=2) <= 4)
        top = np.sum(np.cumprod(dark_rows, axis=1), axis=1)
        bottom = np.sum(np.cumprod(dark_rows[:, ::-1], axis=1), axis=1)
        center_active = np.mean(luma[:, height // 3:2 * height // 3] > 24, axis=(1, 2)) >= .2
        bands = ((top >= 1) & (bottom >= 1) & (top <= height // 3) & (bottom <= height // 3)
                 & (np.abs(top - bottom) <= 1) & center_active)
        # Positive evidence at both edges is needed to call a frame full-screen.
        edges_active = ((np.mean(luma[:, 0] > 24, axis=1) >= .2)
                        & (np.mean(luma[:, -1] > 24, axis=1) >= .2) & center_active)
        current = labels[first:first + len(block)]
        current[bands] = 1
        current[edges_active] = 0
    return labels


def summarize(labels, sample_fps=5, stable_seconds=2, max_unknown_gap_seconds=1):
    labels = np.asarray(labels)
    if (labels.ndim != 1 or not math.isfinite(sample_fps) or sample_fps <= 0
            or not math.isfinite(stable_seconds) or stable_seconds <= 0
            or not math.isfinite(max_unknown_gap_seconds) or max_unknown_gap_seconds < 0
            or not np.isin(labels, [-1, 0, 1]).all()):
        raise ValueError('Invalid signal labels or timing settings')
    minimum = math.ceil(stable_seconds * sample_fps)
    episodes, changes = [], []
    first = 0
    names = {0: 'full_frame', 1: 'letterboxed'}
    for last in range(1, len(labels) + 1):
        if last < len(labels) and labels[last] == labels[first]:
            continue
        label = int(labels[first])
        if label in names and last - first >= minimum:
            episodes.append({'state': names[label], 'first_sample': first,
                             'end_sample_exclusive': last, 'start_seconds': first / sample_fps,
                             'end_seconds_exclusive': last / sample_fps})
        first = last
    for before, after in zip(episodes, episodes[1:]):
        gap = after['first_sample'] - before['end_sample_exclusive']
        if (before['state'] != after['state'] and gap <= max_unknown_gap_seconds * sample_fps):
            changes.append({'classification': 'unclassified_format_change',
                            'from': before['state'], 'to': after['state'],
                            'time_bracket_seconds': [(before['end_sample_exclusive'] - 1) / sample_fps,
                                                     after['first_sample'] / sample_fps],
                            'needs_manual_review': True})
    return {'sample_fps': sample_fps, 'stable_seconds': stable_seconds,
            'counts': {'unknown': int(np.sum(labels == -1)), 'full_frame': int(np.sum(labels == 0)),
                       'letterboxed': int(np.sum(labels == 1))},
            'stable_episodes': episodes, 'format_changes': changes,
            'limitations': ['Format changes are not proof of advertising or separator identity',
                            'Dark scenes, overlays and changing framing can obscure or imitate bands',
                            'Sampled times are not verified editor frame indices; no cuts are produced']}
