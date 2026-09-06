import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.trim_export_queue_client import (
        TrimExportQueueError,
    )
    from video_encoder_ui.trim_export_queue_controller import (
        TrimExportQueueController,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable"
)
class TrimExportQueueControllerTest(
    unittest.TestCase
):
    def test_lists_and_displays_the_queue(self):
        jobs = [
            {
                "id": "trim-1",
                "kind": "trim_export",
                "input_path": "/projects/movie.json",
                "output_path": "/videos/movie.mkv",
                "status": "queued",
                "attempts": 0,
            }
        ]

        client = Mock()
        client.list_jobs.return_value = jobs

        runner = Mock(is_running=False)
        dialog = Mock()
        dialog_class = Mock(
            return_value=dialog
        )
        parent = Mock()

        controller = TrimExportQueueController(
            client=client,
            runner=runner,
            dialog_class=dialog_class,
            parent=parent,
        )

        controller.show()

        client.list_jobs.assert_called_once_with()
        dialog_class.assert_called_once_with(
            jobs,
            parent,
        )
        dialog.set_running.assert_called_once_with(
            False
        )
        dialog.refresh_requested.connect.assert_called_once()
        dialog.start_requested.connect.assert_called_once()
        dialog.exec.assert_called_once_with()

    def test_refreshes_the_displayed_jobs(self):
        jobs = [
            {
                "id": "trim-2",
                "kind": "trim_export",
                "status": "running",
            }
        ]
        client = Mock()
        client.list_jobs.return_value = jobs
        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
        )
        dialog = Mock()

        controller.refresh(dialog)

        client.list_jobs.assert_called_once_with()
        dialog.set_jobs.assert_called_once_with(
            jobs
        )
        dialog.mark_refreshed.assert_called_once()

    def test_starts_the_queue(self):
        runner = Mock()
        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
        )
        dialog = Mock()

        controller.start(dialog)

        runner.start.assert_called_once_with()
        dialog.set_running.assert_called_once_with(
            True
        )

    def test_reports_a_queue_listing_failure(self):
        client = Mock()
        client.list_jobs.side_effect = (
            TrimExportQueueError(
                "database unavailable"
            )
        )
        parent = Mock()

        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
            parent=parent,
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.warning"
        ) as warning:
            controller.show()

        warning.assert_called_once_with(
            parent,
            "File indisponible",
            "database unavailable",
        )

    def test_reports_a_refresh_failure(self):
        client = Mock()
        client.list_jobs.side_effect = (
            TrimExportQueueError(
                "database unavailable"
            )
        )
        parent = Mock()
        dialog = Mock()

        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
            parent=parent,
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.warning"
        ) as warning:
            controller.refresh(dialog)

        warning.assert_called_once_with(
            parent,
            "Actualisation impossible",
            "database unavailable",
        )
        dialog.set_jobs.assert_not_called()

    def test_reports_a_start_failure(self):
        runner = Mock()
        runner.start.side_effect = RuntimeError(
            "worker unavailable"
        )
        parent = Mock()
        dialog = Mock()

        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
            parent=parent,
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.warning"
        ) as warning:
            controller.start(dialog)

        warning.assert_called_once_with(
            parent,
            "Lancement impossible",
            "worker unavailable",
        )
        dialog.set_running.assert_not_called()

    def test_refreshes_the_queue_after_success(self):
        runner = Mock()
        dialog = Mock()
        parent = Mock()

        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
            parent=parent,
        )
        controller.dialog = dialog
        controller.refresh = Mock()

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.information"
        ) as information:
            controller.succeeded()

        dialog.set_running.assert_called_once_with(
            False
        )
        controller.refresh.assert_called_once_with(
            dialog
        )
        information.assert_called_once_with(
            parent,
            "File terminée",
            (
                "Tous les montages en attente "
                "ont été traités."
            ),
        )

    def test_refreshes_the_queue_after_failure(self):
        runner = Mock()
        dialog = Mock()
        parent = Mock()

        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
            parent=parent,
        )
        controller.dialog = dialog
        controller.refresh = Mock()

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.warning"
        ) as warning:
            controller.failed(
                "worker unavailable"
            )

        dialog.set_running.assert_called_once_with(
            False
        )
        controller.refresh.assert_called_once_with(
            dialog
        )
        warning.assert_called_once_with(
            parent,
            "Échec de la file",
            "worker unavailable",
        )

if __name__ == "__main__":
    unittest.main()
