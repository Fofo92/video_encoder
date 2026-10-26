import unittest
from video_encoder_ui.title_convention import title_with_original
from video_encoder_ui.episode_destination import suggested_episode_output
from pathlib import Path


class TitleConventionTest(unittest.TestCase):
    def test_foreign_identical_titles_are_repeated(self):
        self.assertEqual(title_with_original({"french_title": "Boston", "original_title": "Boston",
                                             "countries": ["États-Unis"]}), "Boston (Boston)")

    def test_french_identical_titles_are_not_repeated(self):
        self.assertEqual(title_with_original({"french_title": "Un nouvel espoir", "original_title": "Un nouvel espoir",
                                             "countries": ["France"]}), "Un nouvel espoir")

    def test_unknown_origin_does_not_discard_a_known_original_title(self):
        self.assertEqual(title_with_original({"french_title": "Boston", "original_title": "Boston"}), "Boston (Boston)")

    def test_distinct_titles_and_missing_french_title(self):
        self.assertEqual(title_with_original({"french_title": "Le départ", "original_title": "Departure"}),
                         "Le départ (Departure)")
        self.assertEqual(title_with_original({"original_title": "Departure"}), "Departure")
        self.assertEqual(title_with_original({"french_title": "Boston (Boston)", "original_title": "Boston"}), "Boston (Boston)")

    def test_episode_filename_contains_both_titles(self):
        metadata = {"season_number": 5, "episode_number": 12, "french_title": "Boston", "original_title": "Boston",
                    "countries": ["États-Unis"], "series_titles": []}
        result = suggested_episode_output(metadata, Path("/tmp/test.mkv"), root=Path("/nonexistent-series"))
        self.assertEqual(result.name, "S05 E12 - Boston (Boston).mkv")
