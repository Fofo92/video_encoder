import unittest
import numpy as np
from direct_clip_motifs import discover
from inspect_graphic_motif_context import graphic_context


class GraphicContextTest(unittest.TestCase):
    def test_learns_background_without_assuming_channel_colour(self):
        rng = np.random.default_rng(21)
        for colour in [[.1, .8, .2], [.8, .1, .1], [.94, .94, .94]]:
            frames = rng.random((300, 72), dtype=np.float32)
            frames[80:230] = np.tile(colour, 24)
            result = graphic_context(frames, 150, 200)
            self.assertEqual(result['graphic_start_local_frame'], 80)
            self.assertEqual(result['graphic_end_local_frame_exclusive'], 230)
            self.assertTrue(result['needs_manual_review'])

    def test_dark_context_does_not_extend_a_bright_graphic_region(self):
        frames = np.zeros((300, 72), dtype=np.float32)
        frames[80:230] = .94
        result = graphic_context(frames, 150, 200)
        self.assertEqual(result['graphic_start_local_frame'], 80)
        self.assertEqual(result['graphic_end_local_frame_exclusive'], 230)

    def test_observation_edge_abstains_instead_of_accepting_truncation(self):
        frames = np.ones((300, 72), dtype=np.float32)
        self.assertEqual(graphic_context(frames, 150, 200)['status'], 'unavailable')

    def test_textured_anchor_abstains(self):
        frames = np.random.default_rng(2).random((300, 72), dtype=np.float32)
        self.assertEqual(graphic_context(frames, 150, 200)['status'], 'unavailable')


class DirectCommonCoreTest(unittest.TestCase):
    def features(self, duplicate=False):
        rng = np.random.default_rng(47)
        motif = rng.random((10, 72), dtype=np.float32)
        clips = [rng.random((100, 72), dtype=np.float32) for _ in range(3)]
        for clip in clips:
            clip[30:40] = motif
            if duplicate:
                clip[70:80] = motif
        return clips

    def test_matches_one_anchor_directly_in_every_support_clip(self):
        result = discover(self.features())
        self.assertEqual(len(result), 1)
        self.assertEqual([row['clip_index'] for row in result[0]['occurrences']], [0, 1, 2])

    def test_two_disjoint_identical_cores_are_ambiguous(self):
        self.assertEqual(discover(self.features(duplicate=True)), [])

    def test_two_different_shared_sequences_separated_by_context_are_ambiguous(self):
        rng = np.random.default_rng(82)
        clips = [rng.random((150,72), dtype=np.float32) for _ in range(3)]
        first, second = [rng.random((10,72), dtype=np.float32) for _ in range(2)]
        for clip in clips:
            clip[20:30] = first
            clip[100:110] = second
        self.assertEqual(discover(clips), [])
