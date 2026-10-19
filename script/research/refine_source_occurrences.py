"""Refine scanned motif occurrences on a 25 fps resampled source timeline.

Only outer bounds and the scanner report are accepted, never corrected cuts.
No edit project is produced; separator semantics and editor mapping stay unverified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess

from export_indexed_windows import source_identity
from repeated_visual_sequences import decode, discover
from repeated_sequence_boundaries import refine


def plan(report, start_frame, end_frame):
    if report.get('status') != 'experimental' or report.get('sample_fps') != 5:
        raise ValueError('Expected a full-source experimental scanner report at 5 fps')
    if not 0 <= start_frame < end_frame:
        raise ValueError('Invalid outer bounds')
    windows = []
    for row in report['occurrences']:
        start, end = row['core_start_seconds'], row['core_end_seconds']
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in [start, end]):
            raise ValueError('Invalid scan coordinates')
        if not 0 <= start < end:
            raise ValueError('Invalid scan interval')
        if start * 25 < start_frame or end * 25 > end_frame + 1:
            continue
        first = max(0, round(start * 25) - 150)
        last = round(end * 25) + 150
        windows.append({'name': f'occurrence-{len(windows) + 1}.mp4',
                        'first_sampled_frame': first, 'end_sampled_frame_exclusive': last,
                        'scanner_core_start_seconds': start})
    if not 3 <= len(windows) <= 12:
        raise ValueError('Need three to twelve occurrences inside the outer bounds')
    if any(left['end_sampled_frame_exclusive'] > right['first_sampled_frame']
           for left, right in zip(windows, windows[1:])):
        raise ValueError('Unordered or overlapping observation windows; manual review required')
    return windows


def run(report_path, output, start_frame, end_frame):
    encoded = report_path.read_bytes()
    report = json.loads(encoded)
    windows = plan(report, start_frame, end_frame)
    source = Path(report['source']).resolve(strict=True)
    identity = source_identity(source)
    metadata = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
         'stream=avg_frame_rate', '-of', 'json', str(source)],
        capture_output=True, text=True, check=True,
    )
    if json.loads(metadata.stdout)['streams'][0]['avg_frame_rate'] != '25/1':
        raise ValueError('This pilot requires a 25 average fps source')
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'status': 'prepared', 'source': str(source), 'source_identity': identity,
                'scan_report_sha256': hashlib.sha256(encoded).hexdigest(),
                'outer_bounds': [start_frame, end_frame], 'windows': windows,
                'coordinate_basis': 'FFmpeg fps=25:start_time=0; editor mapping unverified'}
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    labels = ''.join(f'[v{i}]' for i in range(len(windows)))
    filters = [f'[0:v:0]fps=25:start_time=0,split={len(windows)}{labels}']
    for index, row in enumerate(windows):
        filters.append(f"[v{index}]trim=start_frame={row['first_sampled_frame']}:"
                       f"end_frame={row['end_sampled_frame_exclusive']},"
                       f'settb=1/25,setpts=N,scale=960:-2[out{index}]')
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(source),
               '-filter_complex_threads', '1', '-filter_complex', ';'.join(filters)]
    for index, row in enumerate(windows):
        command += ['-map', f'[out{index}]', '-an', '-c:v', 'libx264', '-preset', 'fast',
                    '-crf', '24', '-r', '25', '-enc_time_base', '1:25', '-fps_mode', 'cfr',
                    str(output / row['name'])]
    with (output / 'export.log').open('wb') as log:
        subprocess.run(command, stdout=log, stderr=log, check=True)
    if source_identity(source) != identity:
        raise ValueError('Source changed during extraction')
    paths = [output / row['name'] for row in windows]
    full_rate = [decode(path, sample_fps=25) for path in paths]
    for row, frames in zip(windows, full_rate):
        if len(frames) != row['end_sampled_frame_exclusive'] - row['first_sampled_frame']:
            raise ValueError('Truncated window; no refinement accepted')
    candidates = discover([frames[::5] for frames in full_rate])
    if len(candidates) != 1 or candidates[0]['supporting_clips'] != len(windows):
        raise ValueError('No unique repeated motif in source windows')
    refined = refine(full_rate, candidates[0])
    manifest['refinement'] = refined
    if refined['status'] == 'experimental':
        mapped = []
        for row in refined['occurrences']:
            origin = windows[row['clip_index']]['first_sampled_frame']
            mapped.append({'occurrence': row['clip_index'] + 1,
                           'motif_start_sampled_frame': origin + row['sampled_start_frame'],
                           'motif_end_sampled_frame_exclusive': origin + row['sampled_end_frame_exclusive']})
        manifest['source_motif_limits'] = mapped
    manifest.update(status='experimental', needs_manual_review=True,
                    limitations=['Motif limits are not automatically cut decisions',
                                 'No departure/resume classification or edit project',
                                 'Source resampled timeline is not verified editor coordinates'])
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--start-frame', type=int, required=True)
    parser.add_argument('--end-frame', type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.scan_report, args.output, args.start_frame, args.end_frame), indent=2))
