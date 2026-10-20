import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import numpy as np

from paired_motif_refinement import plan_pair
from refine_source_occurrences import run
from export_indexed_windows import source_identity


def report_for(source):
    return {'status': 'experimental', 'sample_fps': 5, 'source': str(source),
            'source_identity': source_identity(source), 'index_limits_reached': True,
            'candidates': [{'classification': 'unverified_repeated_visual_sequence',
                            'grouping': 'each_occurrence_directly_matches_one_anchor',
                            'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 2}
                                            for value in times]}
                           for times in [[25, 85, 145], [55, 115, 175]]]}


class PairedMotifPlanTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.mkv'
        self.source.write_bytes(b'source')
        self.report = report_for(self.source)

    def test_two_inside_occurrences_per_family_use_outside_support(self):
        windows = plan_pair(self.report, 1, 2, 1750, 4874)
        self.assertEqual(len(windows), 6)
        self.assertEqual(sum(row['inside_coarse_bounds'] for row in windows), 4)
        self.assertEqual([row['family_role'] for row in windows if row['inside_coarse_bounds']],
                         ['departure', 'resume', 'departure', 'resume'])

    def test_reversed_roles_and_same_family_are_rejected_before_decoding(self):
        for departure, resume in [(2, 1), (1, 1), (None, 2)]:
            with self.assertRaises(ValueError):
                plan_pair(self.report, departure, resume, 1750, 4874)

    def test_one_ad_break_is_supported_with_three_recording_wide_repetitions(self):
        windows = plan_pair(self.report, 1, 2, 1750, 3374)
        self.assertEqual(sum(row['inside_coarse_bounds'] for row in windows), 2)

    def test_legacy_unverified_grouping_cannot_be_combined(self):
        self.report['candidates'][0].pop('grouping')
        with self.assertRaisesRegex(ValueError, 'Refresh'):
            plan_pair(self.report, 1, 2, 1750, 4874)


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg unavailable')
class PairedMotifEndToEndTest(unittest.TestCase):
    def test_real_extraction_refines_both_families_and_filters_outside_support(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source.mkv'
            rng = np.random.default_rng(785)
            # Distinct changing contexts prevent extending through identical black padding.
            colors = rng.integers(0, 256, (5000, 1, 1, 3), dtype=np.uint8)
            frames = np.broadcast_to(colors, (5000, 18, 32, 3)).copy()
            for positions in [[25, 85, 145], [55, 115, 175]]:
                motif = rng.integers(0, 256, (50, 18, 32, 3), dtype=np.uint8)
                for second in positions:
                    frames[second * 25:second * 25 + 50] = motif
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'rawvideo', '-pixel_format', 'rgb24',
                            '-video_size', '32x18', '-framerate', '25', '-i', 'pipe:0', '-c:v', 'ffv1', str(source)],
                           input=frames.tobytes(), check=True)
            path = root / 'report.json'
            path.write_text(json.dumps(report_for(source)))
            result = run(path, root / 'output', 1750, 4874, departure_index=1, resume_index=2)
            self.assertEqual(len(result['windows']), 6)
            self.assertEqual(len(result['support_refinements']), 2)
            rows = result['source_motif_limits']
            self.assertEqual([row['family_role'] for row in rows], ['departure', 'resume'] * 2)
            self.assertEqual([(row['motif_start_decoded_frame'], row['motif_end_decoded_frame_exclusive'])
                              for row in rows], [(2125, 2175), (2875, 2925), (3625, 3675), (4375, 4425)])
            from unittest.mock import patch
            with patch('refine_source_occurrences.export_with_progress', side_effect=AssertionError('must reuse')):
                resumed = run(path, root / 'resumed', 1750, 4874, departure_index=1, resume_index=2,
                              reuse_extraction=root / 'output')
            self.assertEqual(resumed['source_motif_limits'], rows)
            self.assertEqual(resumed['reused_extraction']['integrity'], 'verified_sha256')



class PairedContextTest(unittest.TestCase):
    def test_window_edge_is_not_accepted_as_a_cut(self):
        from unittest.mock import patch
        from paired_motif_refinement import refine_pair
        features = [np.zeros((100, 48), np.float32) for _ in range(6)]
        windows = [{'family_role': role, 'first_decoded_frame': index * 1000, 'candidate_index': 1}
                   for index, role in enumerate(['departure'] * 3 + ['resume'] * 3)]
        candidate = {'supporting_clips': 3}
        boundary = {'status': 'experimental', 'occurrences': [
            {'clip_index': index, 'sampled_start_frame': 0, 'sampled_end_frame_exclusive': 50}
            for index in range(3)]}
        with patch('paired_motif_refinement.discover', return_value=[candidate]), \
             patch('paired_motif_refinement.refine', return_value=boundary):
            with self.assertRaisesRegex(ValueError, 'Insufficient context'):
                refine_pair(features, windows, 1, 10000)


class GraphicFallbackTest(unittest.TestCase):
    def test_ambiguous_old_refinement_can_use_direct_graphic_context(self):
        from unittest.mock import patch
        from paired_motif_refinement import refine_pair
        rng = np.random.default_rng(431)
        features, windows = [], []
        for index in range(6):
            role = 'departure' if index % 2 == 0 else 'resume'
            frames = rng.random((300, 1728), dtype=np.float32)
            colour = [.1, .8, .2] if role == 'departure' else [.9, .8, .1]
            frames[80:230] = np.tile(colour, 576)
            # A small moving graphic is repeated; contexts remain independent.
            logo = np.random.default_rng(123 if role == 'departure' else 124).random((50, 30), dtype=np.float32)
            frames[150:200, :30] = logo
            features.append(frames)
            windows.append({'family_role': role, 'first_decoded_frame': index * 500,
                            'candidate_index': 1 if role == 'departure' else 2,
                            'inside_coarse_bounds': index >= 2})
        with patch('paired_motif_refinement.discover', return_value=[]):
            result = refine_pair(features, windows, 750, 2900)
        self.assertTrue(result['refinement']['graphic_fallback_used'])
        self.assertTrue(result['refinement']['needs_manual_review'])
        self.assertEqual([(row['motif_start_decoded_frame'], row['motif_end_decoded_frame_exclusive'])
                          for row in result['source_motif_limits']],
                         [(1080,1230), (1580,1730), (2080,2230), (2580,2730)])

    def test_animated_graphics_without_a_flat_background_abstain(self):
        from unittest.mock import patch
        from paired_motif_refinement import graphic_family
        rng = np.random.default_rng(32)
        frames = [rng.random((300, 1728), dtype=np.float32) for _ in range(3)]
        common = rng.random((50, 1728), dtype=np.float32)
        for value in frames:
            value[150:200] = common
        result = graphic_family(frames, [{'inside_coarse_bounds': True}] * 3, 'ambiguous')
        self.assertEqual(result['status'], 'unavailable')
