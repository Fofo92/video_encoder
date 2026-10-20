import unittest
import numpy as np
from letterbox_signals import classify_frames, summarize


class LetterboxSignalTest(unittest.TestCase):
    def frames(self, count=20, colour=(80, 120, 160), bands=False):
        frames = np.empty((count, 18, 32, 3), dtype=np.uint8)
        frames[:] = colour
        if bands:
            frames[:, :2] = 0
            frames[:, -2:] = 0
        return frames

    def test_detects_bilateral_bands_and_full_frame_without_colour_template(self):
        for colour in [(80,120,160), (100,80,60), (90,90,90)]:
            self.assertTrue(np.all(classify_frames(self.frames(colour=colour, bands=True)) == 1))
            self.assertTrue(np.all(classify_frames(self.frames(colour=colour)) == 0))

    def test_black_frames_are_unknown_not_letterbox(self):
        self.assertTrue(np.all(classify_frames(self.frames(colour=(0,0,0))) == -1))

    def test_one_black_edge_does_not_prove_letterbox_or_full_frame(self):
        frames = self.frames()
        frames[:, :2] = 0
        self.assertTrue(np.all(classify_frames(frames) == -1))

    def test_single_frame_flash_is_not_a_stable_change(self):
        labels = np.ones(41, dtype=np.int8)
        labels[20] = 0
        self.assertEqual(summarize(labels)['format_changes'], [])

    def test_stable_disappearance_and_return_produce_coarse_brackets_not_cuts(self):
        frames = np.concatenate([self.frames(bands=True), self.frames(), self.frames(bands=True)])
        result = summarize(classify_frames(frames))
        self.assertEqual([row['time_bracket_seconds'] for row in result['format_changes']],
                         [[3.8,4.0], [7.8,8.0]])
        self.assertTrue(all(row['needs_manual_review'] for row in result['format_changes']))
        self.assertTrue(all(row['classification'] == 'unclassified_format_change'
                            for row in result['format_changes']))

    def test_long_unknown_gap_does_not_become_a_precise_transition(self):
        labels = np.concatenate([np.ones(20), np.full(10, -1), np.zeros(20)]).astype(np.int8)
        self.assertEqual(summarize(labels)['format_changes'], [])

    def test_batch_size_preserves_measurements(self):
        frames = np.concatenate([self.frames(bands=True), self.frames()])
        np.testing.assert_array_equal(classify_frames(frames, 1), classify_frames(frames, 300))

    def test_unchanging_full_frame_is_not_proof_of_no_advertising(self):
        result = summarize(classify_frames(self.frames()))
        self.assertEqual(result['format_changes'], [])
        self.assertNotIn('ad_free', result)

    def test_malformed_pixels_and_timing_are_rejected(self):
        with self.assertRaises(ValueError):
            classify_frames(self.frames().astype(np.float32))
        with self.assertRaises(ValueError):
            summarize(np.zeros(20), sample_fps=0)
