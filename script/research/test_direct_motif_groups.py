import unittest
import numpy as np
from direct_motif_groups import families, relative_error, window_contrast


class DirectMotifGroupsTest(unittest.TestCase):
    def test_nearby_nodes_from_distinct_families_do_not_bridge_them(self):
        self.assertEqual(families([(0, 200, 1.), (201, 400, 1.)]), [])

    def test_transitive_chain_is_not_one_family(self):
        edges = [(0, 200, 1.), (200, 400, 1.), (400, 600, 1.), (600, 800, 1.)]
        result = families(edges)
        self.assertTrue(result)
        self.assertLessEqual(max(row['supporting_occurrences'] for row in result), 3)
        direct = {frozenset((left, right)) for left, right, _ in edges}
        for group in result:
            anchor = round(group['anchor_core_start_seconds'] * 5)
            for occurrence in group['occurrences']:
                start = round(occurrence['core_start_seconds'] * 5)
                self.assertTrue(start == anchor or frozenset((start, anchor)) in direct)

    def test_dark_unrelated_sequences_do_not_pass_only_because_raw_error_is_small(self):
        self.assertGreater(relative_error(10., 25., 25.), .5)
        self.assertLess(relative_error(10., 1600., 1600.), .5)
        self.assertEqual(relative_error(0., 0., 0.), float('inf'))

    def test_spatially_flat_color_changes_do_not_supply_spatial_contrast(self):
        frames = np.repeat(np.arange(12, dtype=np.uint8)[:, None], 48, axis=1)
        np.testing.assert_equal(window_contrast(frames), np.zeros(3))
