import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        MltFrameMonitor,
        select_media_path,
        select_project_path,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 or MLT is unavailable",
)
class ApplicationDefaultDirectoriesTest(unittest.TestCase):
    def test_new_project_starts_in_the_recordings_directory(self):
        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ) as dialog:
            select_media_path()

        self.assertEqual(
            dialog.call_args.args[2],
            "/commun/to_be_cut",
        )

    def test_open_project_starts_in_the_video_library(self):
        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ) as dialog:
            select_project_path()

        self.assertEqual(
            dialog.call_args.args[2],
            "/videos",
        )

    def test_first_project_save_suggests_the_video_library(self):
        monitor = SimpleNamespace(
            export_status=None,
            project_path=None,
            source_path=Path(
                "/commun/to_be_cut/movie.m2t"
            ),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getSaveFileName",
            return_value=("", ""),
        ) as dialog:
            MltFrameMonitor.save_project(monitor)

        self.assertEqual(
            dialog.call_args.args[2],
            "/videos/movie.json",
        )

    def test_export_uses_the_project_location_for_the_mkv(self):
        project_path = Path(
            "/videos/Series/Season/movie.json"
        )
        audio_preflight_runner = SimpleNamespace(
            is_running=False,
            start=Mock(),
        )
        monitor = SimpleNamespace(
            trim_project_exporter=SimpleNamespace(
                is_running=False
            ),
            audio_preflight_runner=audio_preflight_runner,
            pending_export=None,
            pending_export_mode=None,
            trim_session=SimpleNamespace(
                segments=[object()]
            ),
            source_path=Path(
                "/commun/to_be_cut/source.m2t"
            ),
            project_path=project_path,
            save_project=Mock(return_value=project_path),
            write_project=Mock(return_value=project_path),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getSaveFileName",
            return_value=(
                "/another/location/other.mkv",
                "",
            ),
        ) as dialog:
            MltFrameMonitor.export_project(monitor)

        dialog.assert_not_called()
        monitor.save_project.assert_called_once_with()
        self.assertEqual(
            monitor.pending_export,
            (
                project_path,
                Path(
                    "/videos/Series/Season/movie.mkv"
                ),
            ),
        )
        audio_preflight_runner.start.assert_called_once_with(
            project_path
        )


if __name__ == "__main__":
    unittest.main()
