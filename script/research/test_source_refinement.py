import unittest
from refine_source_occurrences import plan, extraction_filters


class SourceRefinementTest(unittest.TestCase):
    def report(self, starts):
        return {'status': 'experimental', 'sample_fps': 5,
                'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 2}
                                for value in starts]}

    def test_selects_only_scan_hits_inside_outer_bounds_without_corrected_cuts(self):
        windows = plan(self.report([10, 100, 200, 300, 400, 800]), 2025, 12000)
        self.assertEqual([row['first_decoded_frame'] for row in windows], [2350, 4850, 7350, 9850])
        self.assertEqual([row['end_decoded_frame_exclusive'] for row in windows], [2700, 5200, 7700, 10200])

    def test_refuses_ambiguous_overlapping_hits(self):
        with self.assertRaises(ValueError):
            plan(self.report([100, 101, 300]), 0, 10000)

    def test_abstains_with_insufficient_support(self):
        with self.assertRaises(ValueError):
            plan(self.report([100, 200]), 0, 10000)

    def test_rejects_nonfinite_or_reversed_scan_coordinates(self):
        with self.assertRaises(ValueError):
            plan(self.report([float('nan'), 200, 300]), 0, 10000)
        with self.assertRaises(ValueError):
            plan(self.report([100, 200, 300]), 10000, 0)

    def test_timestamp_gap_does_not_create_extra_source_images(self):
        import shutil
        import subprocess
        if not shutil.which('ffmpeg'):
            self.skipTest('FFmpeg unavailable')
        # The input carries 25 actual images with timestamps beginning at 0.52 s.
        # The old fps=start_time=0 chain fills the gap with 13 duplicated images.
        base = ['ffmpeg', '-nostdin', '-v', 'error', '-copyts', '-f', 'lavfi', '-i',
                'testsrc2=size=32x18:rate=25:duration=1,setpts=PTS+0.52/TB']
        old = subprocess.run(base + ['-vf', 'fps=25:start_time=0', '-pix_fmt', 'gray',
                                     '-fps_mode', 'passthrough', '-f', 'rawvideo', 'pipe:1'],
                             capture_output=True, check=True).stdout
        windows = [{'first_decoded_frame': 0, 'end_decoded_frame_exclusive': 25}]
        filters = extraction_filters(windows)
        current = subprocess.run(base + ['-filter_complex', ';'.join(filters), '-map', '[out0]',
                                         '-pix_fmt', 'gray', '-fps_mode', 'passthrough',
                                         '-f', 'rawvideo', 'pipe:1'],
                                 capture_output=True, check=True).stdout
        self.assertEqual(len(old) // (32 * 18), 38)
        self.assertEqual(len(current) // (960 * 540), 25)
