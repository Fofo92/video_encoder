"""Algorithm checks; real-clip results are documented separately."""

import unittest
import numpy as np

from repeated_visual_sequences import discover


class RepeatedVisualSequencesTest(unittest.TestCase):
    def setUp(self):
        self.random = np.random.default_rng(420)
        self.core = self.random.random((14, 48), dtype=np.float32)

    def clips(self):
        result = []
        for start in [5, 13, 20]:
            frames = self.random.random((45, 48), dtype=np.float32)
            frames[start:start + len(self.core)] = self.core
            result.append(frames)
        return result

    def test_discovers_moving_sequence_at_different_positions_without_channel_model(self):
        candidates = discover(self.clips())
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["supporting_clips"], 3)
        self.assertEqual(len(candidates[0]["occurrences"]), 3)

    def test_identical_static_cards_and_black_frames_do_not_supply_motion_evidence(self):
        for value in [0, 0.5, 1]:
            clips = [np.full((30, 48), value, dtype=np.float32) for _ in range(3)]
            self.assertEqual(discover(clips), [])

    def test_ordinary_independent_sequences_do_not_match(self):
        clips = [self.random.random((40, 48), dtype=np.float32) for _ in range(4)]
        self.assertEqual(discover(clips), [])

    def test_two_occurrences_do_not_meet_default_support_requirement(self):
        self.assertEqual(discover(self.clips()[:2]), [])

    def test_frame_order_matters(self):
        self.assertEqual(discover([self.core, self.core[::-1], self.core]), [])

    def test_a_repeated_advertisement_is_not_automatically_labelled_a_separator(self):
        candidates = discover(self.clips())
        self.assertEqual(candidates[0]["classification"], "unverified_repeated_visual_sequence")
        self.assertNotIn("cut", candidates[0])

    def test_short_inputs_abstain_and_invalid_settings_fail(self):
        self.assertEqual(discover([self.core[:2]] * 3), [])
        with self.assertRaises(ValueError):
            discover(self.clips(), window_seconds=0)


if __name__ == "__main__":
    unittest.main()
