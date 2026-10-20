"""Audit cached motion and bilateral-band signals without reading the recording.

No reference project, expected cuts, channel identifier or ad decisions.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np

from letterbox_signals import classify_frames, summarize


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def motion_window_rmse(frames):
    if len(frames) < 10:
        return np.empty(0)
    energy = np.empty(len(frames) - 1, dtype=np.float32)
    for first in range(0, len(energy), 300):
        last = min(len(energy), first + 300)
        delta = frames[first + 1:last + 1].astype(np.float32) - frames[first:last]
        energy[first:last] = np.mean(delta ** 2, axis=1)
    return np.sqrt(np.convolve(energy, np.ones(9) / 9, mode='valid'))


def latest_cache(search_root, source):
    paths = sorted(search_root.glob('**/manifest.json'),
                   key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for path in paths:
        try:
            manifest = json.loads(path.read_text())
            if (manifest.get('status') == 'completed' and manifest.get('cache_sha256')
                    and manifest.get('sampled_frames')
                    and Path(manifest.get('source', '')).resolve() == source.resolve()):
                return path.parent
        except (OSError, ValueError, TypeError):
            continue
    raise ValueError('No completed sealed cache for this source; no decoding was started')


def audit_cache(directory):
    manifest_bytes = (directory / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    count = manifest.get('sampled_frames')
    if manifest.get('status') != 'completed' or type(count) is not int or not 0 < count <= 108000:
        raise ValueError('Expected a completed discovery cache of at most six hours')
    cache = directory / 'sampled-rgb.bin'
    if not cache.is_file():
        cache = Path(manifest.get('cache_path', cache))
    if cache.stat().st_size != count * 1728:
        raise ValueError('Truncated or oversized cached pixels')
    expected_hash = manifest.get('cache_sha256')
    if not expected_hash:
        raise ValueError('This signal audit requires a previously sealed cache')
    before = checksum(cache)
    if before != expected_hash:
        raise ValueError('Cache checksum changed')
    frames = np.memmap(cache, dtype=np.uint8, mode='r', shape=(count, 1728))
    motion = motion_window_rmse(frames)
    labels = classify_frames(frames.reshape(count, 18, 32, 3))
    bands = summarize(labels)
    intervals = []
    for first in range(0, len(motion), 300):
        region = motion[first:first + 300]
        intervals.append({'start_seconds': first / 5,
                          'end_seconds_exclusive': (first + len(region)) / 5,
                          'windows': len(region),
                          'eligible_at_current_motion_threshold': int(np.sum(region >= 2)),
                          'eligible_at_diagnostic_threshold_1': int(np.sum(region >= 1)),
                          'eligible_at_diagnostic_threshold_0_5': int(np.sum(region >= .5))})
    if checksum(cache) != before or (directory / 'manifest.json').read_bytes() != manifest_bytes:
        raise ValueError('Cache or manifest changed during audit')
    return {'status': 'experimental', 'needs_manual_review': True,
            'source_from_manifest': manifest.get('source'),
            'source_identity_from_manifest': manifest.get('source_identity'),
            'original_recording_accessed': False, 'original_source_identity_rechecked': False,
            'sampled_frames': count, 'sample_fps': 5, 'cache_sha256': before,
            'coordinate_basis': 'Resampled FFmpeg timeline; editor alignment unverified',
            'motion_audit': {'current_threshold_rmse': 2, 'window_seconds': 2,
                             'intervals': intervals}, 'band_audit': bands,
            'limitations': ['Diagnostic motion thresholds do not change discovery settings',
                            'A format change or repeated scene is not an advertisement classification',
                            'No source decoding, edit project, cut decision or queue change']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument('--cache', type=Path)
    selector.add_argument('--source', type=Path)
    parser.add_argument('--search-root', type=Path, default=Path('tmp'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory = args.cache if args.cache else latest_cache(args.search_root, args.source)
    result = audit_cache(directory)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(args.output)
