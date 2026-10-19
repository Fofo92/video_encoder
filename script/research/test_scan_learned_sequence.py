import unittest
import numpy as np
from scan_learned_sequence import scan_blocks


class FullSourceScanTest(unittest.TestCase):
    def test_finds_matches_across_blocks_and_at_source_edges(self):
        random = np.random.default_rng(91)
        template = random.random((10, 48), dtype=np.float32)
        source = random.random((100, 48), dtype=np.float32)
        for start in [0, 27, 90]:
            source[start:start + 10] = template
        count, matches = scan_blocks([source[i:i + 30] for i in range(0, 100, 30)], template)
        self.assertEqual(count, 100)
        self.assertEqual([row['best'] for row in matches], [0, 27, 90])

    def test_reversed_order_does_not_match(self):
        template = np.random.default_rng(19).random((10, 48), dtype=np.float32)
        self.assertEqual(scan_blocks([template[::-1]], template)[1], [])

    def test_static_sequence_abstains(self):
        template = np.zeros((10, 48), dtype=np.float32)
        self.assertEqual(scan_blocks([np.zeros((50, 48), dtype=np.float32)], template)[1], [])

    def test_small_blocks_and_short_source(self):
        template = np.random.default_rng(7).random((10, 48), dtype=np.float32)
        self.assertEqual(scan_blocks([template[:3]], template), (3, []))
        count, matches = scan_blocks([template[i:i + 2] for i in range(0, 10, 2)], template)
        self.assertEqual(count, 10)
        self.assertEqual([row['best'] for row in matches], [0])
