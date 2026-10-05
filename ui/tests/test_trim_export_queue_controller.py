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
        dialog.stop_requested.connect.assert_called_once()
        dialog.finish_current_requested.connect.assert_called_once()
        dialog.retry_requested.connect.assert_called_once()
        dialog.remove_requested.connect.assert_called_once()
        dialog.exec.assert_called_once_with()

    def test_forwards_progress_to_the_displayed_dialog(self):
        runner = Mock()
        dialog = Mock()
        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
        )
        controller.dialog = dialog
        event = {
            "stage": "render",
            "step": 42,
            "total": 100,
        }

        controller.progress_changed(event)

        dialog.set_progress.assert_called_once_with(
            event
        )

    def test_forwards_percentage_to_the_displayed_dialog(self):
        runner = Mock()
        dialog = Mock()
        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
        )
        controller.dialog = dialog

        controller.percentage_changed(42)

        dialog.set_percentage.assert_called_once_with(
            42
        )

    def test_ignores_progress_without_a_displayed_dialog(self):
        controller = TrimExportQueueController(
            client=Mock(),
            runner=Mock(),
            dialog_class=Mock(),
        )
        controller.dialog = None

        controller.progress_changed(
            {
                "stage": "render",
                "step": 42,
                "total": 100,
            }
        )

    def test_stops_the_queue_after_confirmation(self):
        runner = Mock()
        dialog = Mock()
        parent = Mock()

        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
            parent=parent,
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.Yes
            ),
        ):
            controller.stop(dialog)

        runner.stop.assert_called_once_with()

    def test_keeps_the_queue_running_when_stop_is_declined(
        self
    ):
        runner = Mock()
        dialog = Mock()

        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.No
            ),
        ):
            controller.stop(dialog)

        runner.stop.assert_not_called()

    def test_requests_a_stop_after_the_current_job(
        self
    ):
        runner = Mock()
        dialog = Mock()
        parent = Mock()

        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
            parent=parent,
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.Yes
            ),
        ):
            controller.finish_current(dialog)

        runner.finish_current.assert_called_once_with()
        dialog.set_finish_current_requested.assert_called_once_with(
            True
        )

    def test_keeps_running_when_the_graceful_stop_is_declined(
        self
    ):
        runner = Mock()
        dialog = Mock()

        controller = TrimExportQueueController(
            client=Mock(),
            runner=runner,
            dialog_class=Mock(),
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.No
            ),
        ):
            controller.finish_current(dialog)

        runner.finish_current.assert_not_called()
        dialog.set_finish_current_requested.assert_not_called()

    def test_refreshes_the_queue_after_interruption(self):
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
            controller.interrupted()

        dialog.set_running.assert_called_once_with(
            False
        )
        controller.refresh.assert_called_once_with(
            dialog
        )
        information.assert_called_once_with(
            parent,
            "File interrompue",
            (
                "Le montage en cours a été interrompu. "
                "Les autres montages restent en attente."
            ),
        )

    def test_refreshes_the_queue_after_a_graceful_stop(self):
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
            controller.stopped()

        dialog.set_running.assert_called_once_with(
            False
        )
        controller.refresh.assert_called_once_with(
            dialog
        )
        information.assert_called_once_with(
            parent,
            "File arrêtée",
            (
                "Le montage en cours est terminé. "
                "Les autres montages restent en attente."
            ),
        )

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

    def test_does_not_retry_when_confirmation_is_declined(
        self
    ):
        client = Mock()
        dialog = Mock()
        job = {
            "input_path": "/projects/movie.json",
            "output_path": "/videos/movie.mkv",
        }

        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.No
            ),
        ):
            controller.retry(dialog, job)

        client.enqueue.assert_not_called()

    def test_reports_a_retry_failure(self):
        client = Mock()
        client.enqueue.side_effect = (
            TrimExportQueueError(
                "output already exists"
            )
        )
        dialog = Mock()
        parent = Mock()
        job = {
            "input_path": "/projects/movie.json",
            "output_path": "/videos/movie.mkv",
        }

        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
            parent=parent,
        )
        controller.refresh = Mock()

        with (
            patch(
                "video_encoder_ui."
                "trim_export_queue_controller."
                "QtWidgets.QMessageBox.question",
                return_value=(
                    QtWidgets.QMessageBox.StandardButton.Yes
                ),
            ),
            patch(
                "video_encoder_ui."
                "trim_export_queue_controller."
                "QtWidgets.QMessageBox.warning"
            ) as warning,
        ):
            controller.retry(dialog, job)

        warning.assert_called_once_with(
            parent,
            "Relance impossible",
            "output already exists",
        )
        controller.refresh.assert_not_called()

    def test_requeues_a_failed_job_after_confirmation(
        self
    ):
        job = {
            "id": "trim-1",
            "input_path": "/projects/movie.json",
            "output_path": "/videos/movie.mkv",
            "status": "failed",
        }
        client = Mock()
        dialog = Mock()
        parent = Mock()

        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
            parent=parent,
        )
        controller.refresh = Mock()

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.Yes
            ),
        ):
            controller.retry(dialog, job)

        client.enqueue.assert_called_once_with(
            "/projects/movie.json",
            "/videos/movie.mkv",
        )
        controller.refresh.assert_called_once_with(
            dialog
        )

    def test_removes_a_queued_job_after_confirmation(self):
        job = {
            "id": "trim-1",
            "input_path": "/projects/movie.json",
            "output_path": "/videos/movie.mkv",
            "status": "queued",
        }
        client = Mock()
        dialog = Mock()
        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
        )
        controller.refresh = Mock()

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.Yes
            ),
        ):
            controller.remove(dialog, job)

        client.remove.assert_called_once_with("trim-1")
        controller.refresh.assert_called_once_with(dialog)

    def test_does_not_remove_when_confirmation_is_declined(self):
        client = Mock()
        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
        )

        with patch(
            "video_encoder_ui."
            "trim_export_queue_controller."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.No
            ),
        ):
            controller.remove(
                Mock(),
                {
                    "id": "trim-1",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                },
            )

        client.remove.assert_not_called()

    def test_reports_a_removal_failure(self):
        client = Mock()
        client.remove.side_effect = TrimExportQueueError(
            "Job is not queued: trim-1"
        )
        parent = Mock()
        controller = TrimExportQueueController(
            client=client,
            runner=Mock(),
            dialog_class=Mock(),
            parent=parent,
        )
        controller.refresh = Mock()

        with (
            patch(
                "video_encoder_ui."
                "trim_export_queue_controller."
                "QtWidgets.QMessageBox.question",
                return_value=(
                    QtWidgets.QMessageBox.StandardButton.Yes
                ),
            ),
            patch(
                "video_encoder_ui."
                "trim_export_queue_controller."
                "QtWidgets.QMessageBox.warning"
            ) as warning,
        ):
            controller.remove(
                Mock(),
                {
                    "id": "trim-1",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                },
            )

        warning.assert_called_once_with(
            parent,
            "Retrait impossible",
            "Job is not queued: trim-1",
        )
        controller.refresh.assert_not_called()

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
