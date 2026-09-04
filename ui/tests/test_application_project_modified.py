import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        MltFrameMonitor,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class ApplicationProjectModifiedTest(unittest.TestCase):
    def test_marks_a_modified_project_in_the_window_title(self):
        monitor = SimpleNamespace(
            source_path=Path(
                "/commun/movie.m2t"
            ),
            project_path=Path(
                "/commun/movie.json"
            ),
            project_modified=True,
            setWindowTitle=Mock(),
        )

        MltFrameMonitor.update_window_title(
            monitor
        )

        monitor.setWindowTitle.assert_called_once_with(
            "video_encoder — Source active : movie.m2t"
            " — Découpage : movie.json *"
        )

    def test_updates_the_title_when_modified_state_changes(self):
        monitor = SimpleNamespace(
            project_modified=False,
            update_window_title=Mock(),
        )

        MltFrameMonitor.set_project_modified(
            monitor,
            True
        )

        self.assertTrue(
            monitor.project_modified
        )
        monitor.update_window_title.assert_called_once_with()

    def test_allows_closing_an_unmodified_project(self):
        monitor = SimpleNamespace(
            project_modified=False,
        )

        self.assertTrue(
            MltFrameMonitor.confirm_unsaved_changes(
                monitor
            )
        )

    def test_saves_a_modified_project_before_closing(self):
        monitor = SimpleNamespace(
            project_modified=True,
            save_project=Mock(
                return_value=Path(
                    "/commun/movie.json"
                )
            ),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.Save
            ),
        ):
            result = (
                MltFrameMonitor.confirm_unsaved_changes(
                    monitor
                )
            )

        self.assertTrue(result)
        monitor.save_project.assert_called_once_with()

    def test_cancels_closing_a_modified_project(self):
        monitor = SimpleNamespace(
            project_modified=True,
            save_project=Mock(),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.Cancel
            ),
        ):
            result = (
                MltFrameMonitor.confirm_unsaved_changes(
                    monitor
                )
            )

        self.assertFalse(result)
        monitor.save_project.assert_not_called()

if __name__ == "__main__":
    unittest.main()
