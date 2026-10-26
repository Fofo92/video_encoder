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
        with patch("video_encoder_ui.project_destination.choose_project_output",
                   return_value=(str(output), "")) as dialog:
            chosen = select_project_output(None, self.root / "capture.mkv")
        self.assertEqual(chosen, output.with_suffix(".mkv"))
        dialog.assert_called_once()
        self.assertFalse(chosen.with_suffix(".json").exists())

    def test_cancelling_writes_nothing(self):
        with patch("video_encoder_ui.project_destination.choose_project_output",
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

    def test_refuses_wrong_extensions_and_reserved_proposals(self):
        for output in [self.root / "movie.json", self.root / "proposal.mkv"]:
            with self.subTest(output=output):
                self.assertIsNotNone(destination_error(output))

    def test_nested_full_path_creates_directories_for_project_and_video(self):
        output = self.root / "Séries TV/_incomplet/Esprits criminels (Criminal Minds)/Saison 07/S07 E01 - Tous pour elle (It Takes a Village).mkv"
        with patch("video_encoder_ui.project_destination.choose_project_output", return_value=(str(output), "")):
            self.assertEqual(output, select_project_output(None, self.root / 'capture.mkv'))
        self.assertTrue(output.parent.is_dir())
        self.assertFalse(output.exists())
        self.assertFalse(output.with_suffix('.json').exists())

    def test_a_file_in_the_directory_path_is_refused_and_preserved(self):
        file = self.root / 'Films'
        file.write_text('preserve')
        self.assertIsNotNone(destination_error(file / 'Drame/film.mkv'))
        self.assertEqual('preserve', file.read_text())

    def test_directory_creation_failure_is_reported_without_returning_a_destination(self):
        output = self.root / 'absent/film.mkv'
        with patch("video_encoder_ui.project_destination.choose_project_output", return_value=(str(output), "")), \
             patch.object(Path, 'mkdir', side_effect=PermissionError('denied')), \
             patch("video_encoder_ui.project_destination.QtWidgets.QMessageBox.warning") as warning:
            self.assertIsNone(select_project_output(None, output))
        warning.assert_called_once()
        self.assertFalse(output.parent.exists())

    def test_real_dialog_accepts_a_full_path_with_missing_nested_directories(self):
        from PySide6 import QtCore, QtWidgets

        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        output = self.root / 'Séries TV/Esprits criminels/Saison 07/S07 E01 - Tous pour elle.mkv'

        def enter_path():
            dialog = application.activeModalWidget()
            dialog.findChild(QtWidgets.QLineEdit, 'project-output-path').setText(str(output))
            dialog.accept()

        QtCore.QTimer.singleShot(0, enter_path)
        self.assertEqual(output, select_project_output(None, self.root / 'capture.mkv'))
        self.assertTrue(output.parent.is_dir())


if __name__ == "__main__":
    unittest.main()
