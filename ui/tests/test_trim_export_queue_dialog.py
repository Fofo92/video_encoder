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

    def test_displays_the_last_refresh_time(self):
        dialog = TrimExportQueueDialog([])

        dialog.mark_refreshed("09:42:17")

        self.assertEqual(
            dialog.refresh_status_label.text(),
            "Dernière actualisation : 09:42:17",
        )

if __name__ == "__main__":
    unittest.main()
