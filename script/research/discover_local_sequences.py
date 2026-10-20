"""Unseeded local repetition pilot. No channel templates or reference cuts.

Searches a fixed spatial grid; correlated local graphics are not ad separators.
Only reads a sealed sampling cache. Never produces an edit project.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from audit_capture_signals import checksum, motion_window_rmse
from direct_motif_groups import families
from discover_source_sequences import bucket_pairs, round_robin


def local_features(frames, window=10):
    count = len(frames) - window + 1
    if count <= 0:
        return np.empty((0, 48)), np.empty(0), np.empty(0)
    # Four temporal bins and four spatial stripes, with RGB retained.
    means = frames.reshape(len(frames), 4, -1, 3).mean(axis=2, dtype=np.float32).reshape(len(frames), 12)
    cumulative = np.vstack([np.zeros((1, 12)), np.cumsum(means, axis=0)])
    desc = np.concatenate([(cumulative[b:b+count]-cumulative[a:a+count])/(b-a)
                           for a,b in [(0,2),(2,5),(5,7),(7,10)]], axis=1)
    # Whole-window standardization tolerates a brightness/contrast change.
    energy = np.mean(frames.astype(np.float32)**2, axis=1)
    mean = np.convolve(frames.mean(axis=1), np.ones(window)/window, mode='valid')
    variance = np.convolve(energy, np.ones(window)/window, mode='valid')-mean**2
    std = np.sqrt(np.maximum(variance, 0))
    return (desc-mean[:,None])/np.maximum(std[:,None], 1), std, motion_window_rmse(frames)



def verified_correlation(a, b):
    """Require both spatial/colour similarity and coherent temporal variation."""
    scale = float(a.std()*b.std())
    if scale <= 0:
        return None
    correlation = float(np.mean((a-a.mean())*(b-b.mean()))/scale)
    if correlation < .8:
        return None
    temporal_a = a-a.mean(axis=0,keepdims=True)
    temporal_b = b-b.mean(axis=0,keepdims=True)
    scale = float(np.sqrt(np.mean(temporal_a**2)*np.mean(temporal_b**2)))
    temporal_correlation = float(np.mean(temporal_a*temporal_b)/scale) if scale > 0 else 0.
    return min(correlation,1.) if temporal_correlation >= .6 else None


def discover_patch(frames, max_pairs=100000, max_bucket=64):
    if type(max_pairs) is not int or not 1 <= max_pairs <= 500000:
        raise ValueError('Pair limit must be between 1 and 500000 per patch')
    if type(max_bucket) is not int or not 2 <= max_bucket <= 256:
        raise ValueError('Bucket limit must be between 2 and 256')
    if frames.ndim != 2 or frames.shape[1] % 12 or frames.dtype != np.uint8:
        raise ValueError('Expected flattened uint8 RGB patch frames')
    desc, std, motion = local_features(frames)
    eligible = np.flatnonzero((std >= 10) & (motion >= 2))
    rng = np.random.default_rng(20261021)
    iterators, saturated = [], False
    for offset in [0, .3]:
        for _ in range(3):
            dims = rng.choice(48, 5, replace=False)
            buckets = {}
            for start in eligible:
                key = tuple(np.floor((desc[start,dims]+offset)/.6).astype(int))
                buckets.setdefault(key, []).append(int(start))
            saturated |= any(len(values)>max_bucket for values in buckets.values())
            iterators.append(round_robin(bucket_pairs(values, max_bucket)
                                        for values in buckets.values() if len(values)>1))
    checked, edges, exhausted = set(), [], False
    for left,right in round_robin(iterators):
        if (left,right) in checked:
            continue
        if len(checked) >= max_pairs:
            exhausted = True
            break
        checked.add((left,right))
        if np.mean((desc[left]-desc[right])**2) > .5:
            continue
        a = frames[left:left+10].astype(np.float32)
        b = frames[right:right+10].astype(np.float32)
        correlation = verified_correlation(a,b)
        if correlation is not None:
            edges.append((left,right,1-correlation))
    groups = families(edges,10)
    for group in groups:
        group['classification'] = 'unverified_repeated_local_sequence'
        group['max_correlation_distance'] = group.pop('max_rmse')
        group['min_correlation_distance'] = group.pop('best_rmse')
        for occurrence in group['occurrences']:
            occurrence['anchor_correlation_distance'] = occurrence.pop('anchor_match_rmse')
    return {'groups': groups, 'comparisons':len(checked), 'eligible_windows':len(eligible),
            'pair_limit_reached':exhausted, 'bucket_limit_reached':saturated}


def run(directory, max_pairs=100000, max_bucket=64):
    manifest_path = directory/'manifest.json'
    original_manifest = manifest_path.read_bytes()
    manifest = json.loads(original_manifest)
    count = manifest.get('sampled_frames')
    if manifest.get('status') != 'completed' or type(count) is not int or not 10 <= count <= 108000:
        raise ValueError('Expected a completed cache of 10 to 108000 frames')
    cache = directory/'sampled-rgb.bin'
    if not cache.is_file():
        cache = Path(manifest.get('cache_path', cache))
    seal = manifest.get('cache_sha256')
    if not seal or cache.stat().st_size != count*1728 or checksum(cache) != seal:
        raise ValueError('Sampling cache is truncated, unsealed or modified')
    pixels = np.memmap(cache, dtype=np.uint8, mode='r', shape=(count,18,32,3))
    patches = []
    for y in range(0,18,6):
        for x in range(0,32,8):
            print(f'Local search: x={x} y={y}', flush=True)
            result = discover_patch(np.ascontiguousarray(pixels[:,y:y+6,x:x+8]).reshape(count,-1),max_pairs,max_bucket)
            patches.append({'crop_xywh':[x,y,8,6],**result})
    if checksum(cache) != seal or manifest_path.read_bytes() != original_manifest:
        raise ValueError('Cache or manifest changed during search')
    return {'status':'experimental','needs_manual_review':True,'sample_fps':5,
            'source_from_manifest':manifest.get('source'),'cache_sha256':seal,
            'original_recording_accessed':False,'patches':patches,
            'coordinate_basis':'Resampled FFmpeg timeline; editor mapping unverified',
            'limitations':['Fixed grid and bounded approximate index may miss local motifs',
                           'Shared graphics, advertisements and film scenes can all match',
                           'No reference cuts or channel templates are inputs',
                           'No separator classification, cut decisions or edit project']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--max-pairs',type=int,default=100000)
    parser.add_argument('--max-bucket',type=int,default=64)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output already exists')
    result = run(args.cache,args.max_pairs,args.max_bucket)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
