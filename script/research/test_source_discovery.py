import unittest
import numpy as np
from discover_source_sequences import discover_source


class SourceDiscoveryTest(unittest.TestCase):
    def source(self):
        rng = np.random.default_rng(201)
        frames = rng.integers(0, 256, (650, 48), dtype=np.uint8)
        motif = rng.integers(0, 256, (15, 48), dtype=np.uint8)
        for start in [40, 250, 500]:
            frames[start:start + 15] = motif
        return frames

    def test_discovers_repeated_movement_without_observation_clips(self):
        result = discover_source(self.source())
        self.assertTrue(any(row['supporting_occurrences'] == 3 for row in result['candidates']))
        row = next(row for row in result['candidates'] if row['supporting_occurrences'] == 3)
        self.assertEqual([item['core_start_seconds'] for item in row['occurrences']], [8, 50, 100])
        self.assertEqual(row['classification'], 'unverified_repeated_visual_sequence')

    def test_does_not_count_nearby_windows_as_independent_occurrences(self):
        self.assertEqual(discover_source(self.source()[:150])['candidates'], [])

    def test_static_source_abstains(self):
        self.assertEqual(discover_source(np.zeros((650, 48), np.uint8))['candidates'], [])

    def test_comparison_limit_is_reported(self):
        result = discover_source(self.source(), max_pairs=1)
        self.assertEqual(result['comparisons'], 1)
        self.assertTrue(result['pair_limit_reached'])

    def test_short_source_abstains(self):
        self.assertEqual(discover_source(self.source()[:5])['candidates'], [])
