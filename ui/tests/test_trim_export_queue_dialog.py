import unittest

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from unittest.mock import Mock
    from video_encoder_ui.trim_export_queue_dialog import (
        TrimExportQueueDialog,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class TrimExportQueueDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtWidgets.QApplication.instance()
            or QtWidgets.QApplication([])
        )

    def test_displays_the_trim_export_jobs(self):
        jobs = [
            {
                "id": "trim-1",
                "kind": "trim_export",
                "input_path": "/commun/Folle Amanda.json",
                "output_path": "/videos/Folle Amanda.mkv",
                "status": "running",
                "attempts": 1,
            },
            {
                "id": "trim-2",
                "kind": "trim_export",
                "input_path": "/commun/Alsace.json",
                "output_path": "/videos/Alsace.mkv",
                "status": "queued",
                "attempts": 0,
            },
        ]

        dialog = TrimExportQueueDialog(jobs)

        self.assertEqual(dialog.jobs_table.rowCount(), 2)
        self.assertEqual(
            dialog.jobs_table.item(0, 0).text(),
            "Folle Amanda.json",
        )
        self.assertEqual(
            dialog.jobs_table.item(0, 1).text(),
            "/videos/Folle Amanda.mkv",
        )
        self.assertEqual(
            dialog.jobs_table.item(0, 2).text(),
            "En cours",
        )
        self.assertEqual(
            dialog.jobs_table.item(1, 2).text(),
            "En attente",
        )

    def test_requests_a_queue_refresh(self):
        dialog = TrimExportQueueDialog([])
        refresh_requested = Mock()
        dialog.refresh_requested.connect(
            refresh_requested
        )

        dialog.refresh_button.click()

        refresh_requested.assert_called_once_with()

    def test_requests_the_queue_start(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "queued",
                    "attempts": 0,
                }
            ]
        )
        start_requested = Mock()
        dialog.start_requested.connect(
            start_requested
        )

        self.assertTrue(
            dialog.start_button.isEnabled()
        )

        dialog.start_button.click()

        start_requested.assert_called_once_with()

    def test_disables_start_without_queued_jobs(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "done",
                    "attempts": 1,
                }
            ]
        )

        self.assertFalse(
            dialog.start_button.isEnabled()
        )

    def test_disables_start_while_queue_is_running(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "queued",
                    "attempts": 0,
                }
            ]
        )

        dialog.set_running(True)

        self.assertFalse(
            dialog.start_button.isEnabled()
        )
        self.assertEqual(
            dialog.start_button.text(),
            "File en cours…",
        )

        dialog.set_running(False)

        self.assertTrue(
            dialog.start_button.isEnabled()
        )
        self.assertEqual(
            dialog.start_button.text(),
            "Lancer la file",
        )

    def test_refreshes_periodically_while_running(self):
        dialog = TrimExportQueueDialog([])

        self.assertFalse(
            dialog.refresh_timer.isActive()
        )

        dialog.set_running(True)

        self.assertTrue(
            dialog.refresh_timer.isActive()
        )
        self.assertEqual(
            dialog.refresh_timer.interval(),
            5_000,
        )

        dialog.set_running(False)

        self.assertFalse(
            dialog.refresh_timer.isActive()
        )

    def test_displays_the_selected_job_error(self):
        error = (
            "command failed: ffmpeg\n"
            "Invalid data found when processing input"
        )
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "/projects/movie.json",
                    "output_path": "/videos/movie.mkv",
                    "status": "failed",
                    "attempts": 1,
                    "error": error,
                }
            ]
        )

        dialog.jobs_table.selectRow(0)

        self.assertEqual(
            dialog.error_details.toPlainText(),
            error,
        )

    def test_displays_the_last_refresh_time(self):
        dialog = TrimExportQueueDialog([])

        dialog.mark_refreshed("09:42:17")

        self.assertEqual(
            dialog.refresh_status_label.text(),
            "Dernière actualisation : 09:42:17",
        )
    def test_requests_retry_for_selected_failed_job(
        self
    ):
        job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "/projects/movie.json",
            "output_path": "/videos/movie.mkv",
            "status": "failed",
            "attempts": 1,
            "error": "ffmpeg failed",
        }
        dialog = TrimExportQueueDialog([job])
        retry_requested = Mock()
        dialog.retry_requested.connect(
            retry_requested
        )

        self.assertFalse(
            dialog.retry_button.isEnabled()
        )

        dialog.jobs_table.selectRow(0)

        self.assertTrue(
            dialog.retry_button.isEnabled()
        )

        dialog.retry_button.click()

        retry_requested.assert_called_once_with(job)

    def test_displays_an_interrupted_job(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "interrupted",
                    "attempts": 1,
                    "error": "trim export interrupted",
                }
            ]
        )

        self.assertEqual(
            dialog.jobs_table.item(0, 2).text(),
            "Interrompu",
        )

    def test_requests_queue_interruption_while_running(
        self
    ):
        dialog = TrimExportQueueDialog([])
        stop_requested = Mock()
        dialog.stop_requested.connect(
            stop_requested
        )

        self.assertFalse(
            dialog.stop_button.isEnabled()
        )

        dialog.set_running(True)

        self.assertTrue(
            dialog.stop_button.isEnabled()
        )

        dialog.stop_button.click()

        stop_requested.assert_called_once_with()

        dialog.set_running(False)

        self.assertFalse(
            dialog.stop_button.isEnabled()
        )

    def test_requests_a_stop_after_the_current_job(
        self
    ):
        dialog = TrimExportQueueDialog([])
        finish_current_requested = Mock()
        dialog.finish_current_requested.connect(
            finish_current_requested
        )

        self.assertFalse(
            dialog.finish_current_button.isEnabled()
        )

        dialog.set_running(True)

        self.assertTrue(
            dialog.finish_current_button.isEnabled()
        )

        dialog.finish_current_button.click()

        finish_current_requested.assert_called_once_with()

        dialog.set_finish_current_requested(True)

        self.assertFalse(
            dialog.finish_current_button.isEnabled()
        )
        self.assertEqual(
            dialog.finish_current_button.text(),
            "Arrêt demandé…",
        )
        self.assertTrue(
            dialog.stop_button.isEnabled()
        )

        dialog.set_running(False)

        self.assertEqual(
            dialog.finish_current_button.text(),
            "Arrêter après le montage en cours",
        )

    def test_requests_retry_for_selected_interrupted_job(
        self
    ):
        job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "interrupted",
            "attempts": 1,
            "error": "trim export interrupted",
        }
        dialog = TrimExportQueueDialog([job])
        retry_requested = Mock()
        dialog.retry_requested.connect(
            retry_requested
        )

        dialog.jobs_table.selectRow(0)

        self.assertTrue(
            dialog.retry_button.isEnabled()
        )

        dialog.retry_button.click()

        retry_requested.assert_called_once_with(job)

    def test_preserves_the_selected_job_during_refresh(self):
        selected_job = {
            "id": "trim-2",
            "kind": "trim_export",
            "input_path": "selected.json",
            "output_path": "selected.mkv",
            "status": "failed",
            "attempts": 1,
            "error": "ffmpeg failed",
        }
        other_job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "other.json",
            "output_path": "other.mkv",
            "status": "done",
            "attempts": 1,
        }
        dialog = TrimExportQueueDialog(
            [other_job, selected_job]
        )
        dialog.jobs_table.selectRow(1)

        refreshed_selected_job = {
            **selected_job,
            "attempts": 2,
        }
        dialog.set_jobs(
            [refreshed_selected_job, other_job]
        )

        self.assertEqual(
            dialog.selected_job()["id"],
            "trim-2",
        )
        self.assertEqual(
            dialog.jobs_table.currentRow(),
            0,
        )

    def test_preserves_the_error_text_selection_during_refresh(
        self
    ):
        error = "command failed: ffmpeg"
        job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "failed",
            "attempts": 1,
            "error": error,
        }
        dialog = TrimExportQueueDialog([job])
        dialog.jobs_table.selectRow(0)
        dialog.error_details.selectAll()

        dialog.set_jobs(
            [
                {
                    **job,
                    "attempts": 2,
                }
            ]
        )

        self.assertEqual(
            dialog.error_details.textCursor().selectedText(),
            error,
        )

    def test_clears_the_error_when_selected_job_disappears(
        self
    ):
        job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "failed",
            "attempts": 1,
            "error": "ffmpeg failed",
        }
        dialog = TrimExportQueueDialog([job])
        dialog.jobs_table.selectRow(0)

        dialog.set_jobs([])

        self.assertIsNone(dialog.selected_job())
        self.assertEqual(
            dialog.error_details.toPlainText(),
            "",
        )

if __name__ == "__main__":
    unittest.main()
