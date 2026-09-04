import unittest

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
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


if __name__ == "__main__":
    unittest.main()
