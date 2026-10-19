"""Check that contextual evidence stays descriptive, including adversarial ads."""

import unittest
import numpy as np

from repeated_sequence_context import audio_similarity, border_transition, characterize


class SequenceContextTest(unittest.TestCase):
    @staticmethod
    def tone(frequency, gain=0.2):
        time = np.arange(24000) / 8000
        return (gain * np.sin(2 * np.pi * frequency * time)).astype(np.float32)

    def test_audio_comparison_tolerates_gain_changes(self):
        self.assertGreater(audio_similarity(self.tone(440), self.tone(440, 0.8)), 0.95)

    def test_different_spectral_content_scores_lower(self):
        self.assertLess(audio_similarity(self.tone(440), self.tone(1600)), 0.8)

    def test_silence_missing_and_short_audio_do_not_supply_positive_evidence(self):
        for audio in [None, np.zeros(24000), np.ones(5)]:
            self.assertIsNone(audio_similarity(audio, self.tone(440)))

    def test_context_direction_changes_when_borders_appear_or_disappear(self):
        pixels = np.ones((250, 18, 32, 3), dtype=np.float32)
        pixels[:100, [0, -1]] = 0
        forward = border_transition(pixels.reshape(250, -1), 100, 175)
        self.assertEqual(forward["direction"], "dark_borders_to_full_frame")
        pixels[:] = 1
        pixels[175:, [0, -1]] = 0
        reverse = border_transition(pixels.reshape(250, -1), 100, 175)
        self.assertEqual(reverse["direction"], "full_frame_to_dark_borders")

    def test_short_or_black_context_is_unresolved(self):
        context = border_transition(np.zeros((30, 1728), dtype=np.float32), 5, 20)
        self.assertEqual(context["direction"], "unresolved")

    def test_repeated_ad_with_identical_audio_and_unchanged_context_is_not_promoted(self):
        features = [np.ones((250, 1728), dtype=np.float32)] * 3
        audio = np.tile(self.tone(440), 3)
        refined = {"status": "experimental", "fps": 25, "occurrences": [
            {"clip_index": i, "sampled_start_frame": 100, "sampled_end_frame_exclusive": 175}
            for i in range(3)
        ]}
        report = characterize(features, [audio] * 3, refined)
        self.assertFalse(report["reciprocal_border_changes"])
        self.assertEqual(report["audio_pairs_compared"], 3)
        self.assertGreater(report["audio_similarity_median"], 0.99)
        self.assertTrue(report["needs_manual_review"])
        self.assertIn("repeated advertisements", report["semantic_status"])
        self.assertNotIn("cut", report)

    def test_absent_boundary_alignment_cannot_be_characterized(self):
        self.assertEqual(characterize([], [], {"status": "unavailable"})["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
