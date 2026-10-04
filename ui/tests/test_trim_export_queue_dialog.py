import unittest

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from unittest.mock import Mock, patch
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
            "Projet indisponible",
        )
        self.assertEqual(
            dialog.jobs_table.item(0, 2).text(),
            "/videos/Folle Amanda.mkv",
        )
        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "En cours",
        )
        self.assertEqual(
            dialog.jobs_table.item(1, 3).text(),
            "En attente",
        )

    def test_displays_progress_on_the_running_job(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "running",
                    "attempts": 1,
                },
                {
                    "id": "trim-2",
                    "kind": "trim_export",
                    "input_path": "next.json",
                    "output_path": "next.mkv",
                    "status": "queued",
                    "attempts": 0,
                },
            ]
        )

        with patch(
            "video_encoder_ui.trim_export_queue_dialog."
            "time.monotonic",
            side_effect=[100.0, 100.0],
        ):
            dialog.set_progress(
                {
                    "stage": "render",
                    "step": 42,
                    "total": 100,
                }
            )

        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Étape 42/100 — render — 00:00",
        )
        self.assertEqual(
            dialog.jobs_table.item(1, 3).text(),
            "En attente",
        )

    def test_displays_real_percentage_on_the_running_job(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "running",
                    "attempts": 1,
                }
            ]
        )
        with patch(
            "video_encoder_ui.trim_export_queue_dialog."
            "time.monotonic",
            side_effect=[100.0, 100.0, 142.0],
        ):
            dialog.set_progress(
                {
                    "stage": "video",
                    "step": 1,
                    "total": 4,
                }
            )
            dialog.set_percentage(42)

        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Étape 1/4 — Vidéo — 42 % — 00:42",
        )

    def test_preserves_progress_when_job_becomes_running(self):
        queued_job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "queued",
            "attempts": 0,
        }
        dialog = TrimExportQueueDialog([queued_job])

        with patch(
            "video_encoder_ui.trim_export_queue_dialog."
            "time.monotonic",
            side_effect=[100.0, 100.0, 142.0],
        ):
            dialog.set_progress(
                {
                    "stage": "video",
                    "step": 1,
                    "total": 4,
                }
            )
            dialog.set_percentage(15)
            dialog.set_jobs(
                [
                    {
                        **queued_job,
                        "status": "running",
                        "attempts": 1,
                    }
                ]
            )

        self.assertEqual(
            dialog.progress_job_id,
            "trim-1",
        )
        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Étape 1/4 — Vidéo — 15 % — 00:00",
        )

    def test_preserves_percentage_only_during_refresh(self):
        job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "running",
            "attempts": 1,
        }
        dialog = TrimExportQueueDialog([job])

        dialog.set_percentage(15)
        dialog.set_jobs([job])

        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "En cours — 15 %",
        )

    def test_displays_total_duration_for_completed_job(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "done",
                    "attempts": 1,
                    "started_at":
                        "2026-10-04T10:00:00+02:00",
                    "finished_at":
                        "2026-10-04T10:09:17+02:00",
                }
            ]
        )

        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Terminé — 09:17",
        )

    def test_displays_french_audio_language(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "running",
                    "attempts": 1,
                }
            ]
        )

        with patch(
            "video_encoder_ui.trim_export_queue_dialog."
            "time.monotonic",
            return_value=100.0,
        ):
            dialog.set_progress(
                {
                    "stage": "audio",
                    "step": 3,
                    "total": 5,
                    "track": 1,
                    "tracks": 2,
                    "role": "french",
                }
            )

        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Étape 3/5 — Audio 1/2 (fra) — 00:00",
        )

    def test_displays_original_audio_language(self):
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "running",
                    "attempts": 1,
                }
            ]
        )

        with patch(
            "video_encoder_ui.trim_export_queue_dialog."
            "time.monotonic",
            return_value=100.0,
        ):
            dialog.set_progress(
                {
                    "stage": "audio",
                    "step": 4,
                    "total": 5,
                    "track": 2,
                    "tracks": 2,
                    "role": "original",
                }
            )

        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Étape 4/5 — Audio 2/2 (qaa) — 00:00",
        )

    def test_status_column_fits_progress_text(self):
        dialog = TrimExportQueueDialog([])

        required_width = (
            dialog.jobs_table.fontMetrics().horizontalAdvance(
                dialog.STATUS_WIDTH_SAMPLE
            )
            + 24
        )

        self.assertGreaterEqual(
            dialog.jobs_table.columnWidth(3),
            required_width,
        )
        self.assertGreaterEqual(
            dialog.width(),
            1_100,
        )

    def test_formats_elapsed_progress_over_an_hour(self):
        self.assertEqual(
            TrimExportQueueDialog.format_elapsed_time(
                3_661
            ),
            "1:01:01",
        )

    def test_resets_elapsed_time_for_the_next_job(self):
        first_job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "running",
            "attempts": 1,
        }
        second_job = {
            "id": "trim-2",
            "kind": "trim_export",
            "input_path": "next.json",
            "output_path": "next.mkv",
            "status": "queued",
            "attempts": 0,
        }
        dialog = TrimExportQueueDialog(
            [first_job, second_job]
        )

        with patch(
            "video_encoder_ui.trim_export_queue_dialog."
            "time.monotonic",
            return_value=100.0,
        ):
            dialog.set_progress(
                {"stage": "video"}
            )

        self.assertEqual(
            dialog.progress_started_at,
            100.0,
        )

        dialog.set_jobs(
            [
                {**first_job, "status": "done"},
                {**second_job, "status": "running"},
            ]
        )

        self.assertIsNone(dialog.progress_started_at)
        self.assertIsNone(dialog.progress_event)
        self.assertEqual(
            dialog.progress_job_id,
            "trim-2",
        )

    def test_preserves_progress_during_queue_refresh(self):
        job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "running",
            "attempts": 1,
        }
        dialog = TrimExportQueueDialog([job])
        with patch(
            "video_encoder_ui.trim_export_queue_dialog."
            "time.monotonic",
            side_effect=[100.0, 100.0, 142.0],
        ):
            dialog.set_progress(
                {
                    "stage": "render",
                    "step": 42,
                    "total": 100,
                }
            )
            dialog.set_jobs([job])

        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Étape 42/100 — render — 00:42",
        )

    def test_clears_progress_when_no_job_is_running(self):
        running_job = {
            "id": "trim-1",
            "kind": "trim_export",
            "input_path": "movie.json",
            "output_path": "movie.mkv",
            "status": "running",
            "attempts": 1,
        }
        dialog = TrimExportQueueDialog([running_job])
        dialog.set_progress(
            {
                "stage": "render",
                "step": 42,
                "total": 100,
            }
        )

        dialog.set_jobs(
            [
                {
                    **running_job,
                    "status": "done",
                }
            ]
        )

        self.assertIsNone(dialog.progress_event)
        self.assertEqual(
            dialog.jobs_table.item(0, 3).text(),
            "Terminé",
        )

    def test_displays_the_project_source_names(self):
        source_names = Mock(
            return_value=(
                "source-a.m2t · source-b.m2t"
            )
        )
        dialog = TrimExportQueueDialog(
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "/projects/movie.json",
                    "output_path": "/videos/movie.mkv",
                    "status": "queued",
                    "attempts": 0,
                }
            ],
            source_names=source_names,
        )

        source_names.assert_called_once_with(
            "/projects/movie.json"
        )
        self.assertEqual(
            dialog.jobs_table.item(0, 1).text(),
            "source-a.m2t · source-b.m2t",
        )

    def test_allows_every_column_to_be_resized(self):
        dialog = TrimExportQueueDialog([])
        header = dialog.jobs_table.horizontalHeader()

        for column in range(
            dialog.jobs_table.columnCount()
        ):
            self.assertEqual(
                header.sectionResizeMode(column),
                QtWidgets.QHeaderView.ResizeMode.Interactive,
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
            dialog.jobs_table.item(0, 3).text(),
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
