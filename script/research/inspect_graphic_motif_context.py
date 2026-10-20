"""Inspect flat graphic context around repeated cores; never produce edit cuts.

Research diagnostic only. A repeated logo may belong to an advertisement or a
programme. A uniform background is not proof of a separator. No channel colours,
reference cut positions or expected number of ad breaks are used.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from direct_clip_motifs import discover
from repeated_visual_sequences import decode


def graphic_context(frames, core_start, core_end):
    if frames.ndim != 2 or frames.shape[1] % 3 or not 0 <= core_start < core_end <= len(frames):
        raise ValueError('Invalid decoded core')
    rgb = frames.reshape(len(frames), -1, 3)
    center = (core_start + core_end) // 2
    # Learn the background from this occurrence, not from a channel template.
    background = np.median(rgb[center], axis=0)
    coverage = (np.max(np.abs(rgb - background), axis=2) <= 40 / 255).mean(axis=1)
    valid = coverage >= .8
    if not valid[center]:
        return {'status': 'unavailable', 'reason': 'Core has no dominant flat background'}
    left, right = center, center + 1
    while left > 0 and valid[left - 1]:
        left -= 1
    while right < len(frames) and valid[right]:
        right += 1
    if left == 0 or right == len(frames):
        return {'status': 'unavailable', 'reason': 'Graphic region reaches observation edge'}
    if not 50 <= right - left <= 250:
        return {'status': 'unavailable', 'reason': 'Graphic region outside experimental 2–10 second range'}
    return {'status': 'experimental', 'needs_manual_review': True,
            'graphic_start_local_frame': left, 'graphic_end_local_frame_exclusive': right,
            'minimum_background_coverage': float(coverage[left:right].min())}


def inspect(directory):
    manifest_bytes = (directory / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    windows = manifest['windows']
    frames, hashes = [], {}
    for row in windows:
        name = row['name']
        if Path(name).name != name:
            raise ValueError('Expected a local observation filename')
        path = directory / name
        value = decode(path, sample_fps=25)
        if len(value) != row['end_decoded_frame_exclusive'] - row['first_decoded_frame']:
            raise ValueError('Truncated observation window')
        frames.append(value)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    observations = []
    for role in ['departure', 'resume']:
        indices = [i for i, row in enumerate(windows) if row['family_role'] == role]
        candidates = discover([frames[i][::5] for i in indices])
        if len(candidates) != 1:
            observations.append({'family_role': role, 'status': 'unavailable',
                                 'reason': 'No unambiguous direct common core'})
            continue
        for core in candidates[0]['occurrences']:
            index = indices[core['clip_index']]
            row = windows[index]
            if not row['inside_coarse_bounds']:
                continue
            result = graphic_context(frames[index], round(core['core_start_seconds'] * 25),
                                     round(core['core_end_seconds'] * 25))
            if result['status'] == 'experimental':
                origin = row['first_decoded_frame']
                result['graphic_start_decoded_frame'] = origin + result['graphic_start_local_frame']
                result['graphic_end_decoded_frame_exclusive'] = origin + result['graphic_end_local_frame_exclusive']
            observations.append({'name': row['name'], 'family_role': role, **result})
    return {'status': 'experimental', 'needs_manual_review': True, 'source': manifest['source'],
            'outer_bounds': manifest['outer_bounds'],
            'coordinate_basis': manifest['coordinate_basis'],
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(), 'window_sha256': hashes,
            'observations': observations,
            'limitations': ['Graphic region limits are not validated film boundaries',
                            'Thresholds are exploratory; no independent capture validation',
                            'Families still selected upstream; no automatic ad classification',
                            'No source reread, edit project, queue change or encoding']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.directory)
    # Keep the original extraction manifest intact.
    with args.output.open('x') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print(json.dumps(result, indent=2))
