import unittest
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
    from video_encoder_ui.trim_export_queue_client import (
        TrimExportQueueError,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class ApplicationTrimExportQueueTest(
    unittest.TestCase
):
    def test_lists_and_displays_trim_exports(self):
        jobs = [
            {
                "id": "trim-1",
                "kind": "trim_export",
                "input_path": "/commun/movie.json",
                "output_path": "/videos/movie.mkv",
                "status": "queued",
                "attempts": 0,
            }
        ]
        client = Mock()
        client.list_jobs.return_value = jobs
        monitor = SimpleNamespace(
            trim_export_queue_client=client,
        )
        dialog = Mock()

        with patch(
            "video_encoder_ui.application."
            "TrimExportQueueDialog",
            return_value=dialog,
        ) as dialog_class:
            MltFrameMonitor.show_trim_export_queue(
                monitor
            )

        client.list_jobs.assert_called_once_with()
        dialog_class.assert_called_once_with(
            jobs,
            monitor,
        )
        dialog.exec.assert_called_once_with()

    def test_reports_a_queue_listing_failure(self):
        client = Mock()
        client.list_jobs.side_effect = (
            TrimExportQueueError(
                "database unavailable"
            )
        )
        monitor = SimpleNamespace(
            trim_export_queue_client=client,
        )

        with (
            patch(
                "video_encoder_ui.application."
                "QtWidgets.QMessageBox.warning"
            ) as warning,
            patch(
                "video_encoder_ui.application."
                "TrimExportQueueDialog"
            ) as dialog_class,
        ):
            MltFrameMonitor.show_trim_export_queue(
                monitor
            )

        warning.assert_called_once_with(
            monitor,
            "File indisponible",
            "database unavailable",
        )
        dialog_class.assert_not_called()

if __name__ == "__main__":
    unittest.main()
