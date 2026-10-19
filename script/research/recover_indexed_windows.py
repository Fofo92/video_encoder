"""Recover indexed MP4 windows whose final image is hidden by an edit list.

Requires the complete expected decoded images with ignore_editlist=1. Preserves
every decoded pixel via lossless encoding and verifies the ordered frame hashes.
Never opens the original recording or modifies an existing file.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def frame_hashes(path, ignore_editlist=False):
    command = ['ffmpeg', '-nostdin', '-v', 'error']
    if ignore_editlist:
        command += ['-ignore_editlist', '1']
    command += ['-i', str(path), '-map', '0:v:0', '-an', '-fps_mode', 'passthrough', '-f', 'framemd5', '-']
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return [line.split(',')[-1].strip() for line in result.stdout.splitlines()
            if line and not line.startswith('#')]


def recover(input_directory, output):
    manifest = json.loads((input_directory / 'frame-map.json').read_text())
    if manifest.get('fps') != 25 or not manifest.get('windows'):
        raise ValueError('Unsupported indexed-window manifest')
    hashes = {}
    for row in manifest['windows']:
        if Path(row['name']).name != row['name']:
            raise ValueError('Window names must be simple filenames')
        path = input_directory / row['name']
        frames = frame_hashes(path, ignore_editlist=True)
        if len(frames) != row['expected_frame_count']:
            raise ValueError('Missing encoded images: cannot recover this window without the source')
        hashes[row['name']] = frames
    output.mkdir(parents=True, exist_ok=False)
    manifest['status'] = 'recovering_container'
    manifest['recovery'] = {'original_recording_accessed': False, 'ordered_decoded_pixels_verified': False}
    target_manifest = output / 'frame-map.json'
    target_manifest.write_text(json.dumps(manifest, indent=2) + '\n')
    for row in manifest['windows']:
        path = input_directory / row['name']
        fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
        command = ['ffmpeg', '-nostdin', '-v', 'error', '-n', '-ignore_editlist', '1', '-i', str(path),
                   '-map', '0:v:0', '-an', '-vf', 'settb=1/25,setpts=N', '-r', '25',
                   '-enc_time_base', '1:25', '-fps_mode', 'cfr', '-c:v', 'libx264',
                   '-preset', 'fast', '-crf', '0', str(output / row['name'])]
        with (output / (row['name'] + '.recovery.log')).open('wb') as log:
            subprocess.run(command, check=True, stdout=log, stderr=log)
        if fingerprint != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError('Input window changed during recovery')
        if frame_hashes(output / row['name']) != hashes[row['name']]:
            raise ValueError('Recovery did not preserve all decoded images in order')
        row['input_window_sha256'] = fingerprint
    manifest['status'] = 'container_recovered_editor_alignment_unverified'
    manifest['recovery']['ordered_decoded_pixels_verified'] = True
    target_manifest.write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(recover(options.input, options.output), indent=2))
