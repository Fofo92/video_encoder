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
        MediaInspectionError,
        MltFrameMonitor,
    )

@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class ApplicationSourceInformationTest(
    unittest.TestCase
):
    def test_inspects_and_displays_every_source(self):
        source = SimpleNamespace(
            path=Path("/commun/movie.m2t")
        )
        inspected_source = {
            "path": "/commun/movie.m2t",
            "inspection": {
                "duration": 3600
            }
        }
        client = Mock()
        client.inspect.return_value = (
            inspected_source
        )
        monitor = SimpleNamespace(
            trim_session=SimpleNamespace(
                sources=(source,)
            ),
            media_inspection_client=client,
        )
        dialog = Mock()

        with patch(
            "video_encoder_ui.application."
            "SourceInformationDialog",
            return_value=dialog,
        ) as dialog_class:
            MltFrameMonitor.show_source_information(
                monitor
            )

        client.inspect.assert_called_once_with(
            source.path
        )
        dialog_class.assert_called_once_with(
            [inspected_source],
            monitor,
        )
        dialog.exec.assert_called_once_with()

    def test_reports_an_inspection_failure(self):
        source = SimpleNamespace(
            path=Path("/commun/movie.m2t")
        )
        client = Mock()
        client.inspect.side_effect = (
            MediaInspectionError(
                "source unavailable"
            )
        )
        monitor = SimpleNamespace(
            trim_session=SimpleNamespace(
                sources=(source,)
            ),
            media_inspection_client=client,
        )

        with (
            patch(
                "video_encoder_ui.application."
                "QtWidgets.QMessageBox.warning"
            ) as warning,
            patch(
                "video_encoder_ui.application."
                "SourceInformationDialog"
            ) as dialog_class,
        ):
            MltFrameMonitor.show_source_information(
                monitor
            )

        warning.assert_called_once_with(
            monitor,
            "Inspection impossible",
            "source unavailable",
        )
        dialog_class.assert_not_called()

if __name__ == "__main__":
    unittest.main()
