"""Refine scanned motif occurrences using decoded source frame indices.

Only outer bounds and the scanner report are accepted, never corrected cuts.
No edit project is produced; separator semantics and editor mapping stay unverified.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

from export_indexed_windows import source_identity
from repeated_visual_sequences import decode, discover
from repeated_sequence_boundaries import refine


def select_candidate(report, candidate_index=None):
    if 'candidates' not in report:
        if candidate_index is not None:
            raise ValueError('Candidate selection requires a discovery report')
        return report
    if type(candidate_index) is not int or not 1 <= candidate_index <= len(report['candidates']):
        raise ValueError('Choose a candidate explicitly with --candidate (one-based)')
    selected = report['candidates'][candidate_index - 1]
    if selected.get('classification') != 'unverified_repeated_visual_sequence':
        raise ValueError('Unsupported candidate classification')
    return {**report, 'occurrences': selected['occurrences']}


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
                        'first_decoded_frame': first, 'end_decoded_frame_exclusive': last,
                        'scanner_core_start_seconds': start})
    if not 3 <= len(windows) <= 12:
        raise ValueError('Need three to twelve occurrences inside the outer bounds')
    if any(left['end_decoded_frame_exclusive'] > right['first_decoded_frame']
           for left, right in zip(windows, windows[1:])):
        raise ValueError('Unordered or overlapping observation windows; manual review required')
    return windows


def extraction_filters(windows):
    # Count the original decoded images before resetting timestamps. An fps filter
    # here could duplicate/drop images and invalidate origin + local-index mapping.
    labels = ''.join(f'[v{i}]' for i in range(len(windows)))
    filters = [f'[0:v:0]split={len(windows)}{labels}']
    for index, row in enumerate(windows):
        filters.append(f"[v{index}]trim=start_frame={row['first_decoded_frame']}:"
                       f"end_frame={row['end_decoded_frame_exclusive']},"
                       f'settb=1/25,setpts=N,scale=960:-2[out{index}]')
    return filters


def run(report_path, output, start_frame, end_frame, candidate_index=None):
    encoded = report_path.read_bytes()
    report = select_candidate(json.loads(encoded), candidate_index)
    windows = plan(report, start_frame, end_frame)
    source = Path(report['source']).resolve(strict=True)
    identity = source_identity(source)
    if report.get('source_identity', identity) != identity:
        raise ValueError('Source changed since discovery')
    metadata = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
         'stream=avg_frame_rate,start_time:format=start_time', '-of', 'json', str(source)],
        capture_output=True, text=True, check=True,
    )
    timing = json.loads(metadata.stdout)
    if timing['streams'][0]['avg_frame_rate'] != '25/1':
        raise ValueError('This pilot requires a 25 average fps source')
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'status': 'prepared', 'source': str(source), 'source_identity': identity,
                'scan_report_sha256': hashlib.sha256(encoded).hexdigest(),
                'selected_candidate': candidate_index,
                'discovery_limits_reached': report.get('index_limits_reached', False),
                'outer_bounds': [start_frame, end_frame], 'windows': windows,
                'coordinate_basis': 'FFmpeg decoded source frame index; editor mapping unverified',
                'source_timing_metadata': timing,
                'window_localization': 'scanner seconds times 25 are approximate centers only'}
    manifest_path = output / 'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    filters = extraction_filters(windows)
    command = ['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(source),
               '-filter_complex_threads', '1', '-filter_complex', ';'.join(filters)]
    for index, row in enumerate(windows):
        command += ['-map', f'[out{index}]', '-an', '-c:v', 'libx264', '-preset', 'fast',
                    '-crf', '24', '-r', '25', '-enc_time_base', '1:25', '-fps_mode', 'cfr',
                    str(output / row['name'])]
    print('REVIEW_STAGE ' + json.dumps({'step': 1, 'label': 'Lecture et extraction de la source'}), file=sys.stderr, flush=True)
    with (output / 'export.log').open('wb') as log:
        subprocess.run(command, stdout=log, stderr=log, check=True)
    if source_identity(source) != identity:
        raise ValueError('Source changed during extraction')
    paths = [output / row['name'] for row in windows]
    print('REVIEW_STAGE ' + json.dumps({'step': 2, 'label': 'Préparation des images des raccords'}), file=sys.stderr, flush=True)
    full_rate = [decode(path, sample_fps=25) for path in paths]
    for row, frames in zip(windows, full_rate):
        if len(frames) != row['end_decoded_frame_exclusive'] - row['first_decoded_frame']:
            raise ValueError('Truncated window; no refinement accepted')
    print('REVIEW_STAGE ' + json.dumps({'step': 3, 'label': 'Comparaison et affinement des raccords'}), file=sys.stderr, flush=True)
    candidates = discover([frames[::5] for frames in full_rate])
    if len(candidates) != 1 or candidates[0]['supporting_clips'] != len(windows):
        raise ValueError('No unique repeated motif in source windows')
    refined = refine(full_rate, candidates[0])
    manifest['refinement'] = refined
    if refined['status'] == 'experimental':
        mapped = []
        for row in refined['occurrences']:
            origin = windows[row['clip_index']]['first_decoded_frame']
            mapped.append({'occurrence': row['clip_index'] + 1,
                           'motif_start_decoded_frame': origin + row['sampled_start_frame'],
                           'motif_end_decoded_frame_exclusive': origin + row['sampled_end_frame_exclusive']})
        manifest['source_motif_limits'] = mapped
    manifest.update(status='experimental', needs_manual_review=True,
                    limitations=['Motif limits are not automatically cut decisions',
                                 'No departure/resume classification or edit project',
                                 'Decoded source frame indices still require editor alignment checks'])
    manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--candidate', type=int)
    parser.add_argument('--start-frame', type=int, required=True)
    parser.add_argument('--end-frame', type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.scan_report, args.output, args.start_frame, args.end_frame, args.candidate), indent=2))
