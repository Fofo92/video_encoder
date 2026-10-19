"""Reproduce a shortened MP4 edit list while retaining the encoded final image."""

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from recover_indexed_windows import frame_hashes, recover


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools required')
class IndexedRecoveryTest(unittest.TestCase):
    def test_hidden_last_image_is_recovered_without_changing_pixels_or_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'old'
            source.mkdir()
            path = source / 'window.mp4'
            subprocess.run(
                ['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i',
                 'testsrc2=s=64x64:r=25:d=2', '-c:v', 'libx264', str(path)], check=True,
            )
            data = bytearray(path.read_bytes())
            position = data.index(b'elst')
            self.assertEqual(data[position + 4], 0)
            self.assertEqual(int.from_bytes(data[position + 8:position + 12], 'big'), 1)
            duration = int.from_bytes(data[position + 12:position + 16], 'big')
            self.assertEqual(duration, 2000)
            data[position + 12:position + 16] = (duration - 40).to_bytes(4, 'big')
            path.write_bytes(data)
            manifest = {'fps': 25, 'status': 'prepared', 'editor_alignment': 'requires_visual_verification',
                        'windows': [{'name': 'window.mp4', 'expected_frame_count': 50}]}
            (source / 'frame-map.json').write_text(json.dumps(manifest))
            self.assertEqual(len(frame_hashes(path)), 49)
            original_hashes = frame_hashes(path, ignore_editlist=True)
            self.assertEqual(len(original_hashes), 50)
            fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
            report = recover(source, root / 'recovered')
            self.assertTrue(report['recovery']['ordered_decoded_pixels_verified'])
            self.assertFalse(report['recovery']['original_recording_accessed'])
            self.assertEqual(frame_hashes(root / 'recovered' / 'window.mp4'), original_hashes)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), fingerprint)
            with self.assertRaises(FileExistsError):
                recover(source, root / 'recovered')
            manifest['windows'][0]['expected_frame_count'] = 51
            (source / 'frame-map.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Missing encoded images'):
                recover(source, root / 'missing-image')
            self.assertFalse((root / 'missing-image').exists())


if __name__ == '__main__':
    unittest.main()
