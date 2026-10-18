import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from video_encoder_ui.project_destination import destination_error, select_project_output
except ModuleNotFoundError:
    select_project_output = None


@unittest.skipIf(select_project_output is None, "PySide6 is unavailable")
class ProjectDestinationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def test_one_choice_adds_extension_and_preserves_spaces_and_episode_title(self):
        output = self.root / "S04 E05 - Suis ta route"
        with patch("video_encoder_ui.project_destination.QtWidgets.QFileDialog.getSaveFileName",
                   return_value=(str(output), "")) as dialog:
            chosen = select_project_output(None, self.root / "capture.mkv")
        self.assertEqual(chosen, output.with_suffix(".mkv"))
        dialog.assert_called_once()
        self.assertFalse(chosen.with_suffix(".json").exists())

    def test_cancelling_writes_nothing(self):
        with patch("video_encoder_ui.project_destination.QtWidgets.QFileDialog.getSaveFileName",
                   return_value=("", "")):
            self.assertIsNone(select_project_output(None, self.root / "movie.mkv"))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_existing_project_is_allowed_only_when_it_is_the_loaded_project(self):
        project = self.root / "movie.json"
        project.write_text("existing montage")
        self.assertIsNone(destination_error(project.with_suffix(".mkv"), project))
        self.assertIsNotNone(destination_error(project.with_suffix(".mkv")))
        self.assertEqual(project.read_text(), "existing montage")

    def test_refuses_video_collisions_and_dangling_project_symlinks(self):
        output = self.root / "movie.mkv"
        output.write_text("encoded video")
        self.assertIsNotNone(destination_error(output))
        output.unlink()
        output.with_suffix(".json").symlink_to(self.root / "absent.json")
        self.assertIsNotNone(destination_error(output))
        output.symlink_to(self.root / "absent.mkv")
        self.assertIsNotNone(destination_error(output))

    def test_refuses_missing_directories_wrong_extensions_and_reserved_proposals(self):
        for output in [self.root / "absent/movie.mkv", self.root / "movie.json", self.root / "proposal.mkv"]:
            with self.subTest(output=output):
                self.assertIsNotNone(destination_error(output))


if __name__ == "__main__":
    unittest.main()
