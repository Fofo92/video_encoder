"""Algorithm checks; real-clip results are documented separately."""

import unittest
import shutil
import subprocess
import tempfile
from pathlib import Path
import numpy as np

from repeated_visual_sequences import decode, discover
from repeated_sequence_boundaries import refine
from repetition_holdout import evaluate


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

    def test_extends_shared_sequence_without_extending_into_different_contexts(self):
        clips = self.clips()
        candidate = discover(clips)[0]
        refined = refine(clips, candidate, fps=5)
        self.assertEqual(refined["status"], "experimental")
        self.assertEqual([(row["sampled_start_frame"], row["sampled_end_frame_exclusive"])
                          for row in refined["occurrences"]], [(5, 19), (13, 27), (20, 34)])
        self.assertEqual(refined["duration_seconds"], 2.8)

    def test_repeated_advertisement_still_has_unknown_semantics_after_refinement(self):
        clips = self.clips()
        refined = refine(clips, discover(clips)[0], fps=5)
        self.assertEqual(refined["classification"], "unverified_shared_run")
        self.assertIn("Cannot distinguish", refined["semantic_status"])
        self.assertTrue(refined["needs_manual_review"])

    def test_withheld_occurrence_can_be_found_without_participating_in_discovery(self):
        clips = self.clips()
        frames = self.random.random((45, 48), dtype=np.float32)
        frames[9:23] = self.core
        clips.append(frames)
        report = evaluate(clips)
        self.assertTrue(all(len(row["matches"]) == 1 for row in report["results"]))
        clips[-1] = self.random.random((45, 48), dtype=np.float32)
        self.assertEqual(evaluate(clips)["results"][-1]["matches"], [])

    def test_holdout_does_not_silently_lower_its_support_requirement(self):
        self.assertEqual(evaluate(self.clips())["status"], "unavailable")

    def test_refinement_abstains_on_multiple_occurrences_per_clip_or_missing_alignment(self):
        clips = self.clips()
        candidate = discover(clips)[0]
        duplicate = dict(candidate, occurrences=candidate["occurrences"] * 2)
        self.assertEqual(refine(clips, duplicate, fps=5)["status"], "unavailable")
        clips[-1] = self.random.random(clips[-1].shape, dtype=np.float32)
        self.assertEqual(refine(clips, candidate, fps=5)["status"], "unavailable")

    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg tools required")
    def test_delayed_video_is_explicitly_sampled_from_media_time_zero(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "delayed.mp4"
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi", "-i",
                 "testsrc2=size=64x36:rate=25:duration=2", "-f", "lavfi", "-i",
                 "anullsrc=r=8000:cl=mono", "-map", "0:v:0", "-map", "1:a:0", "-t", "3",
                 "-vf", "setpts=PTS+1/TB", "-fps_mode", "passthrough", "-c:v", "libx264",
                 "-c:a", "aac", str(path)], check=True,
            )
            frames = decode(path, sample_fps=25)
            self.assertEqual(len(frames), 75)
            np.testing.assert_array_equal(frames[0], frames[24])


if __name__ == "__main__":
    unittest.main()
