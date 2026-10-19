"""Check indexed export against a synthetic video with a known colour boundary."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import numpy as np

from export_indexed_windows import export, plan
from repeated_visual_sequences import decode


class WindowPlanTest(unittest.TestCase):
    @staticmethod
    def project(path, last=174):
        return {"format": "video_encoder.trim_project", "version": 2,
                "sources": [{"id": "source", "path": str(path)}], "timeline": [
                    {"type": "segment", "source_id": "source", "start_frame": 0, "end_frame": 74},
                    {"type": "segment", "source_id": "source", "start_frame": 100, "end_frame": last}]}

    def test_departure_is_first_excluded_frame_and_resume_is_first_retained_frame(self):
        _, rows = plan(self.project('/source'), radius=25)
        self.assertEqual([(row['first_decoded_frame'], row['end_decoded_frame_exclusive'])
                          for row in rows], [(50, 100), (75, 125)])
        self.assertTrue(all(row['reviewed_boundary_local_frame'] == 25 for row in rows))

    def test_invalid_or_overlapping_segments_fail(self):
        project = self.project('/source')
        project['timeline'][1]['start_frame'] = 70
        with self.assertRaises(ValueError):
            plan(project)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg tools required')
class IndexedExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        cls.root = Path(cls.directory.name)
        cls.source = cls.root / 'source.mp4'
        subprocess.run(
            ['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x36:r=25:d=3',
             '-f', 'lavfi', '-i', 'color=c=blue:s=64x36:r=25:d=3', '-f', 'lavfi', '-i',
             'color=c=green:s=64x36:r=25:d=3', '-filter_complex', '[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]',
             '-map', '[v]', '-c:v', 'libx264', '-video_track_timescale', '90000', str(cls.source)], check=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_export_preserves_known_frame_boundary_and_existing_output_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / 'reviewed.json'
            project.write_text(json.dumps(WindowPlanTest.project(self.source)))
            original = self.source.read_bytes()
            report = export(project, root / 'windows', radius=25)
            self.assertEqual(report['editor_alignment'], 'requires_visual_verification')
            frames = decode(root / 'windows' / 'departure-1.mp4', sample_fps=25)
            colours = frames.reshape(-1, 18, 32, 3).mean(axis=(1, 2))
            self.assertEqual(len(colours), 50)
            self.assertTrue(np.all(colours[:25, 0] > 0.7))
            self.assertTrue(np.all(colours[25:, 2] > 0.7))
            self.assertEqual(self.source.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                export(project, root / 'windows', radius=25)

    def test_truncated_export_never_receives_a_complete_frame_map(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            project = WindowPlanTest.project(self.source, last=300)
            project['timeline'][1]['start_frame'] = 210
            path = root / 'reviewed.json'
            path.write_text(json.dumps(project))
            with self.assertRaisesRegex(ValueError, 'Truncated'):
                export(path, root / 'windows', radius=25)
            manifest = json.loads((root / 'windows' / 'frame-map.json').read_text())
            self.assertEqual(manifest['status'], 'prepared')


if __name__ == '__main__':
    unittest.main()
