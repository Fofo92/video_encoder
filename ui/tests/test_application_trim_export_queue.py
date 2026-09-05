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
            trim_export_queue_runner=SimpleNamespace(
                is_running=False,
            ),
            trim_export_queue_dialog=None,
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

    def test_refreshes_the_displayed_jobs(self):
        jobs = [
            {
                "id": "trim-2",
                "kind": "trim_export",
                "input_path": "/commun/next.json",
                "output_path": "/videos/next.mkv",
                "status": "running",
                "attempts": 1,
            }
        ]
        client = Mock()
        client.list_jobs.return_value = jobs
        monitor = SimpleNamespace(
            trim_export_queue_client=client,
        )
        dialog = Mock()

        MltFrameMonitor.refresh_trim_export_queue(
            monitor,
            dialog,
        )

        client.list_jobs.assert_called_once_with()
        dialog.set_jobs.assert_called_once_with(
            jobs
        )

    def test_starts_the_trim_export_queue(self):
        runner = Mock()
        monitor = SimpleNamespace(
            trim_export_queue_runner=runner,
        )
        dialog = Mock()

        MltFrameMonitor.start_trim_export_queue(
            monitor,
            dialog,
        )

        runner.start.assert_called_once_with()
        dialog.set_running.assert_called_once_with(
            True
        )

    def test_refreshes_the_queue_after_success(self):
        dialog = Mock()
        monitor = SimpleNamespace(
            trim_export_queue_dialog=dialog,
        )

        with (
            patch.object(
                MltFrameMonitor,
                "refresh_trim_export_queue",
            ) as refresh,
            patch(
                "video_encoder_ui.application."
                "QtWidgets.QMessageBox.information"
            ) as information,
        ):
            MltFrameMonitor.trim_export_queue_succeeded(
                monitor
            )

        dialog.set_running.assert_called_once_with(
            False
        )
        refresh.assert_called_once_with(
            monitor,
            dialog,
        )
        information.assert_called_once_with(
            monitor,
            "File terminée",
            "Tous les montages en attente ont été traités.",
        )

    def test_refreshes_the_queue_after_failure(self):
        dialog = Mock()
        monitor = SimpleNamespace(
            trim_export_queue_dialog=dialog,
        )

        with (
            patch.object(
                MltFrameMonitor,
                "refresh_trim_export_queue",
            ) as refresh,
            patch(
                "video_encoder_ui.application."
                "QtWidgets.QMessageBox.warning"
            ) as warning,
        ):
            MltFrameMonitor.trim_export_queue_failed(
                monitor,
                "worker unavailable",
            )

        dialog.set_running.assert_called_once_with(
            False
        )
        refresh.assert_called_once_with(
            monitor,
            dialog,
        )
        warning.assert_called_once_with(
            monitor,
            "Échec de la file",
            "worker unavailable",
        )

    def test_prevents_closing_while_queue_is_running(self):
        monitor = SimpleNamespace(
            trim_export_queue_runner=SimpleNamespace(
                is_running=True,
            )
        )
        event = Mock()

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.information"
        ) as information:
            MltFrameMonitor.closeEvent(
                monitor,
                event,
            )

        event.ignore.assert_called_once_with()
        information.assert_called_once_with(
            monitor,
            "File en cours",
            (
                "La file des montages est en cours "
                "d’exécution.\n"
                "Attends sa fin avant de fermer "
                "video_encoder."
            ),
        )

if __name__ == "__main__":
    unittest.main()
