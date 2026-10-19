"""Experimental unseeded discovery of repeated moving cores in one recording.

No observation clips, reference project, channel template or cut coordinates.
Approximate candidate indexing can miss motifs. Repetition is not ad semantics.
"""
import argparse
from collections import deque
from itertools import combinations
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

from export_indexed_windows import source_identity
from direct_motif_groups import families, window_contrast, relative_error
from scan_learned_sequence import source_blocks


def descriptors(frames, window=10):
    """Ordered temporal and spatial RGB averages, used only to shortlist comparisons."""
    count = len(frames) - window + 1
    if count <= 0:
        return np.empty((0, 48), dtype=np.float32)
    means = np.mean(frames.reshape(len(frames), 4, -1, 3), axis=2, dtype=np.float32) / 255
    means = means.reshape(len(frames), 12)
    cumulative = np.vstack([np.zeros((1, 12)), np.cumsum(means, axis=0)])
    return np.concatenate([(cumulative[b:b + count] - cumulative[a:a + count]) / (b - a)
                           for a, b in [(0, 2), (2, 5), (5, 7), (7, 10)]], axis=1)


def round_robin(iterables):
    pending = deque(iter(value) for value in iterables)
    while pending:
        iterator = pending.popleft()
        try:
            yield next(iterator)
        except StopIteration:
            continue
        pending.append(iterator)


def bucket_pairs(starts, limit, separation=150):
    # Sample the complete time span instead of retaining only the first entries.
    if len(starts) > limit:
        starts = [starts[index] for index in np.linspace(0, len(starts) - 1, limit, dtype=int)]
    return ((int(left), int(right)) for left, right in combinations(starts, 2)
            if right - left >= separation)


def overlapping_runs(starts, window):
    runs = []
    for start in sorted(starts):
        if not runs or start > runs[-1][-1] + window:
            runs.append([])
        runs[-1].append(start)
    return runs


def discover_source(frames, max_pairs=500000, max_bucket=128):
    if not 1 <= max_pairs <= 5000000 or not 1 <= max_bucket <= 1024:
        raise ValueError('Search limits outside supported research bounds')
    window, minimum_separation = 10, 150
    if frames.ndim != 2 or frames.shape[1] % 12:
        raise ValueError('Expected flattened RGB frames')
    desc = descriptors(frames)
    if not len(desc):
        return {'candidates': [], 'comparisons': 0, 'index_limits_reached': False}
    # Reject static windows before indexing, using rolling motion energy.
    energy = np.empty(len(frames) - 1, dtype=np.float32)
    for first in range(0, len(energy), 1500):
        last = min(len(energy), first + 1500)
        delta = frames[first + 1:last + 1].astype(np.float32) - frames[first:last]
        energy[first:last] = np.mean((delta / 255) ** 2, axis=1)
    motion = np.sqrt(np.convolve(energy, np.ones(9) / 9, mode='valid')) * 255
    eligible = np.flatnonzero(motion >= 2)
    rng = np.random.default_rng(20261019)
    tables = [(rng.choice(48, 6, replace=False), offset) for offset in [0, .04] for _ in range(4)]
    contrast = window_contrast(frames, window)
    edges, checked = [], set()
    saturated, exhausted = False, False
    table_iterators = []
    for dims, offset in tables:
        buckets = {}
        for start in eligible:
            key = tuple(np.floor((desc[start, dims] + offset) / .08).astype(int))
            buckets.setdefault(key, []).append(int(start))
        saturated |= any(len(bucket) > max_bucket for bucket in buckets.values())
        table_iterators.append(round_robin(bucket_pairs(bucket, max_bucket, minimum_separation)
                                          for bucket in buckets.values() if len(bucket) > 1))
    # Each table and bucket gets turns. Dense early material cannot consume the
    # entire budget before later buckets or alternative index tables are visited.
    for previous, start in round_robin(table_iterators):
        pair = (previous, start)
        if pair in checked:
            continue
        if len(checked) >= max_pairs:
            exhausted = True
            break
        checked.add(pair)
        if np.sqrt(np.mean((desc[start] - desc[previous]) ** 2)) * 255 > 20:
            continue
        difference = frames[start:start + window].astype(np.float32)
        difference -= frames[previous:previous + window]
        rmse = float(np.sqrt(np.mean(difference ** 2)))
        if rmse <= 15 and relative_error(rmse, contrast[previous], contrast[start]) <= .5:
            edges.append((pair[0], pair[1], rmse))
    return {'candidates': families(edges, window),
            'comparisons': len(checked), 'index_strategy': 'balanced_direct_contrast_v3',
            'max_relative_rmse': .5, 'index_limits_reached': saturated or exhausted,
            'bucket_limit_reached': saturated, 'pair_limit_reached': exhausted}


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def load_cache(directory, source):
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest.get('status') != 'completed':
        raise ValueError('Cannot reuse an incomplete discovery cache')
    if (Path(manifest['source']).resolve() != source.resolve()
            or manifest['source_identity'] != source_identity(source)):
        raise ValueError('Cache belongs to a different or modified source')
    count = manifest['sampled_frames']
    if type(count) is not int or not 0 < count <= 108000:
        raise ValueError('Invalid cached frame count')
    cache = Path(manifest.get('cache_path', directory / 'sampled-rgb.bin')).resolve(strict=True)
    if cache.stat().st_size != count * 1728:
        raise ValueError('Truncated or oversized discovery cache')
    checksum = digest(cache)
    expected = manifest.get('cache_sha256')
    if expected is not None and checksum != expected:
        raise ValueError('Discovery cache checksum changed')
    return cache, count, checksum, ('verified_sha256' if expected else 'legacy_cache_no_original_digest')


def run(source, output, reuse_cache=None, max_pairs=500000, max_bucket=128):
    source = source.resolve(strict=True)
    identity = source_identity(source)
    # Validate before creating a new output. Legacy caches can only be checked
    # for source identity and size; their historical byte integrity is unknown.
    reused = load_cache(reuse_cache, source) if reuse_cache else None
    output.mkdir(parents=True, exist_ok=False)
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps({'status': 'preparing', 'source': str(source)}))
    if reused:
        cache, count, checksum, integrity = reused
        print(f'Reusing {count} sampled frames; no source decoding', file=sys.stderr)
    else:
        cache = output / 'sampled-rgb.bin'
        count = 0
        print('Decoding source at 5 sampled frames/second...', file=sys.stderr)
        with cache.open('wb') as stream:
            for block in source_blocks(source):
                count += len(block)
                if count > 108000:
                    raise ValueError('Research limit: six hours; diagnostics retained')
                np.rint(block * 255).astype(np.uint8).tofile(stream)
                if count % 6000 == 0:
                    print(f'Sampled {count / 5:.0f} seconds of recording', file=sys.stderr)
        checksum, integrity = digest(cache), 'sealed_after_decoding'
    if source_identity(source) != identity:
        raise ValueError('Source changed during decoding or cache checks')
    cache_manifest = {'status': 'completed', 'source': str(source), 'source_identity': identity,
                      'sampled_frames': count, 'cache_path': str(cache.resolve()),
                      'cache_sha256': checksum, 'cache_integrity': integrity}
    # Cache completion is independent of motif discovery, allowing a retry after
    # an interrupted search without decoding the source again.
    manifest_path.write_text(json.dumps(cache_manifest, indent=2) + '\n')
    print(f'Discovering repeated cores in {count} sampled frames...', file=sys.stderr)
    frames = np.memmap(cache, dtype=np.uint8, mode='r', shape=(count, 1728)) if count else np.empty((0, 1728), np.uint8)
    result = discover_source(frames, max_pairs=max_pairs, max_bucket=max_bucket)
    if digest(cache) != checksum or source_identity(source) != identity:
        raise ValueError('Source or cache changed during discovery')
    result.update(status='experimental', needs_manual_review=True, source=str(source),
                  source_identity=identity, sample_fps=5, sampled_frames=count,
                  reused_cache=reused is not None, cache_integrity=integrity,
                  search_limits={'max_pairs': max_pairs, 'max_bucket': max_bucket},
                  limitations=['Approximate index may miss motifs even without a reported limit',
                               'Repeated advertisements and programme sequences may match',
                               'No separator classification, cut decisions or project',
                               'Times use the resampled FFmpeg timeline, not editor frame indices'])
    (output / 'resultat.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--reuse-cache', type=Path)
    parser.add_argument('--max-pairs', type=int, default=500000)
    parser.add_argument('--max-bucket', type=int, default=128)
    args = parser.parse_args()
    print(json.dumps(run(args.source, args.output, args.reuse_cache, args.max_pairs, args.max_bucket), indent=2))
