import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

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


if __name__ == "__main__":
    unittest.main()
