"""Anchor-verified motif families; no transitive or temporal bridge merging."""
from collections import defaultdict
import numpy as np


def window_contrast(frames, window=10):
    energy = np.empty(len(frames), dtype=np.float32)
    for first in range(0, len(frames), 1500):
        block = frames[first:first + 1500].astype(np.float32).reshape(-1, frames.shape[1] // 3, 3)
        energy[first:first + len(block)] = np.mean(np.var(block, axis=1), axis=1)
    return np.convolve(energy, np.ones(window) / window, mode='valid')


def relative_error(rmse, left_variance, right_variance):
    contrast = np.sqrt((left_variance + right_variance) / 2)
    return rmse / contrast if contrast > 0 else float('inf')


def families(edges, window=10, min_occurrences=3):
    neighbors = defaultdict(dict)
    for left, right, score in edges:
        neighbors[left][right] = score
        neighbors[right][left] = score
    groups = []
    for anchor, matches in neighbors.items():
        runs = []
        for start, score in sorted([(anchor, 0.)] + list(matches.items())):
            if not runs or start - runs[-1][-1][0] > window:
                runs.append([])
            runs[-1].append((start, score))
        # One directly verified representative for each overlapping occurrence.
        occurrences = [min(run, key=lambda item: item[1]) for run in runs]
        if len(occurrences) >= min_occurrences:
            groups.append((anchor, occurrences))
    groups.sort(key=lambda row: (-len(row[1]), max(score for _, score in row[1])))
    accepted = []
    for anchor, occurrences in groups:
        starts = [start for start, _ in occurrences]
        duplicate = False
        for _, old in accepted:
            shared = sum(any(abs(start - previous) <= window for previous, _ in old) for start in starts)
            if shared / max(len(starts), len(old)) >= .8:
                duplicate = True
                break
        if not duplicate:
            accepted.append((anchor, occurrences))
    return [{'classification': 'unverified_repeated_visual_sequence',
             'grouping': 'each_occurrence_directly_matches_one_anchor',
             'anchor_core_start_seconds': anchor / 5,
             'supporting_occurrences': len(occurrences),
             'best_rmse': round(min(score for start, score in occurrences if start != anchor), 3),
             'max_rmse': round(max(score for _, score in occurrences), 3),
             'occurrences': [{'core_start_seconds': start / 5, 'core_end_seconds': (start + window) / 5,
                              'anchor_match_rmse': round(score, 3)} for start, score in occurrences]}
            for anchor, occurrences in accepted]
