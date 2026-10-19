"""Experimental full-source search for a motif learned from observation clips.

No reference project or expected cut positions are accepted. This is motif search,
not blind discovery or automatic advertisement classification.
"""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np

from repeated_visual_sequences import decode, discover, window_scores, motion_scores


def scan_blocks(blocks, template, max_rmse=15, min_motion=2):
    """Bound memory and retain overlap so block boundaries cannot hide matches."""
    window = len(template)
    if window < 2 or min_motion <= 0 or max_rmse <= 0:
        raise ValueError('Invalid search settings')
    tail = np.empty((0, template.shape[1]), dtype=np.float32)
    consumed, matches = 0, []
    for block in blocks:
        frames = np.concatenate([tail, block])
        origin = consumed - len(tail)
        if len(frames) >= window:
            scores = window_scores(frames, template, window)[:, 0]
            motion = motion_scores(frames, window)
            for start in np.flatnonzero((scores <= max_rmse) & (motion >= min_motion)):
                matches.append((origin + int(start), float(scores[start])))
        consumed += len(block)
        tail = frames[-(window - 1):]
    groups = []
    for start, score in matches:
        if not groups or start > groups[-1]['last'] + 1:
            groups.append({'first': start, 'last': start, 'best': start, 'score': score})
        else:
            group = groups[-1]
            group['last'] = start
            if score < group['score']:
                group.update(best=start, score=score)
    return consumed, groups


def source_blocks(path, block_frames=1500):
    size = block_frames * 1728
    # stderr on disk prevents pipe deadlock; never buffer the full decoded capture.
    with tempfile.TemporaryFile() as diagnostics:
        process = subprocess.Popen([
            'ffmpeg', '-nostdin', '-v', 'error', '-i', str(path), '-map', '0:v:0',
            '-an', '-sn', '-vf', 'fps=5:start_time=0,scale=32:18',
            '-pix_fmt', 'rgb24', '-fps_mode', 'passthrough', '-f', 'rawvideo', 'pipe:1',
        ], stdout=subprocess.PIPE, stderr=diagnostics)
        try:
            pending = b''
            while True:
                chunk = process.stdout.read(size - len(pending))
                if not chunk:
                    if len(pending) % 1728:
                        raise ValueError('Incomplete decoded frame')
                    if pending:
                        yield np.frombuffer(pending, np.uint8).reshape(-1, 1728).astype(np.float32) / 255
                    break
                pending += chunk
                if len(pending) == size:
                    yield np.frombuffer(pending, np.uint8).reshape(-1, 1728).astype(np.float32) / 255
                    pending = b''
            if process.wait() != 0:
                diagnostics.seek(0)
                raise RuntimeError(diagnostics.read().decode(errors='replace')[-4000:])
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--clips', type=Path, nargs='+', required=True)
    options = parser.parse_args()
    paths = [path.resolve(strict=True) for path in options.clips]
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate observation clips')
    features = [decode(path) for path in paths]
    candidates = discover(features)
    if len(candidates) != 1:
        raise ValueError('Expected one unambiguous learned motif; review observation clips')
    occurrence = candidates[0]['occurrences'][0]
    start = round(occurrence['core_start_seconds'] * 5)
    template = features[occurrence['clip_index']][start:start + 10]
    source = options.source.resolve(strict=True)
    before = source.stat()
    count, matches = scan_blocks(source_blocks(source), template)
    after = source.stat()
    identity = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    if identity(before) != identity(after):
        raise ValueError('Source changed during analysis')
    print(json.dumps({
        'status': 'experimental', 'needs_manual_review': True,
        'source': str(source), 'observation_clips': [str(path) for path in paths],
        'sample_fps': 5, 'sampled_frames': count,
        'occurrences': [{'core_start_seconds': row['best'] / 5,
                         'core_end_seconds': (row['best'] + 10) / 5,
                         'rmse': round(row['score'], 3)} for row in matches],
        'limitations': ['Learned from manually selected clips, not blind motif discovery',
                        'Times use the resampled FFmpeg timeline, not verified editor frame indices',
                        'Repeated ads may match; no automatic cut or project is produced'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
