import unittest
from refine_source_occurrences import plan


class SourceRefinementTest(unittest.TestCase):
    def report(self, starts):
        return {'status': 'experimental', 'sample_fps': 5,
                'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 2}
                                for value in starts]}

    def test_selects_only_scan_hits_inside_outer_bounds_without_corrected_cuts(self):
        windows = plan(self.report([10, 100, 200, 300, 400, 800]), 2025, 12000)
        self.assertEqual([row['first_sampled_frame'] for row in windows], [2350, 4850, 7350, 9850])
        self.assertEqual([row['end_sampled_frame_exclusive'] for row in windows], [2700, 5200, 7700, 10200])

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
