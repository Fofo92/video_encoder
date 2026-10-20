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

    def test_live_progress_counts_source_images_beyond_extracted_window(self):
        import contextlib
        import io
        import json
        import shutil
        import tempfile
        from pathlib import Path
        from refine_source_occurrences import export_with_progress
        if not shutil.which('ffmpeg'):
            self.skipTest('FFmpeg unavailable')
        windows = [{'first_decoded_frame': 0, 'end_decoded_frame_exclusive': 25}]
        command = ['ffmpeg', '-nostdin', '-v', 'info', '-nostats', '-f', 'lavfi', '-i',
                   'testsrc2=size=32x18:rate=25:duration=20.04',
                   '-filter_complex_threads', '1', '-filter_complex',
                   ';'.join(extraction_filters(windows, observe=True)),
                   '-map', '[out0]', '-f', 'null', '-']
        progress = io.StringIO()
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stderr(progress):
            export_with_progress(command, Path(directory) / 'export.log')
        rows = [json.loads(line.removeprefix('REVIEW_STAGE '))
                for line in progress.getvalue().splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertIn('501 images', rows[-1]['label'])
        self.assertTrue(all(row['step'] == 1 for row in rows))


class DiscoveryCandidateSelectionTest(unittest.TestCase):
    def report(self):
        return {'status': 'experimental', 'sample_fps': 5, 'source': '/source.m2t',
                'index_limits_reached': True,
                'candidates': [{'classification': 'unverified_repeated_visual_sequence',
                                'occurrences': [{'core_start_seconds': 10, 'core_end_seconds': 12}]},
                               {'classification': 'unverified_repeated_visual_sequence',
                                'occurrences': [{'core_start_seconds': start, 'core_end_seconds': start + 3}
                                                for start in [100, 200, 300, 400]]}]}

    def test_explicit_choice_flows_into_refinement_without_reference_cuts(self):
        from refine_source_occurrences import select_candidate
        selected = select_candidate(self.report(), 2)
        self.assertEqual(len(plan(selected, 0, 12000)), 4)
        self.assertTrue(selected['index_limits_reached'])
        self.assertEqual(selected['source'], '/source.m2t')

    def test_does_not_implicitly_choose_the_most_frequent_group(self):
        from refine_source_occurrences import select_candidate
        for index in [None, 0, 3]:
            with self.assertRaises(ValueError):
                select_candidate(self.report(), index)

    def test_old_learned_scan_reports_remain_supported(self):
        from refine_source_occurrences import select_candidate
        report = {'occurrences': []}
        self.assertIs(select_candidate(report), report)


class ReuseObservationTest(unittest.TestCase):
    def test_reuse_checks_hypothesis_and_sealed_content(self):
        import hashlib
        import json
        import tempfile
        from pathlib import Path
        from refine_source_occurrences import reuse_windows
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous, output = root / 'previous', root / 'output'
            previous.mkdir()
            output.mkdir()
            expected = {'source': 'source', 'source_identity': {'bytes': 1},
                        'windows': [{'name': 'observation.mp4'}]}
            clip = previous / 'observation.mp4'
            clip.write_bytes(b'original')
            record = {**expected, 'window_sha256': {'observation.mp4': hashlib.sha256(clip.read_bytes()).hexdigest()}}
            (previous / 'manifest.json').write_text(json.dumps(record))
            result = reuse_windows(previous, output, expected)
            self.assertEqual(result['integrity'], 'verified_sha256')
            self.assertEqual((output / clip.name).read_bytes(), b'original')
            with self.assertRaisesRegex(ValueError, 'hypothesis'):
                reuse_windows(previous, output, {**expected, 'outer_bounds': [1, 2]})
            clip.write_bytes(b'modified')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                reuse_windows(previous, output, expected)
