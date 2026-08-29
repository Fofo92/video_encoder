import unittest
from pathlib import Path

from PySide6 import QtCore

from video_encoder_ui.trim_project_exporter import (
    TrimProjectExporter,
)


class TrimProjectExporterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtCore.QCoreApplication.instance()
            or QtCore.QCoreApplication([])
        )

    def wait_for_export(self, exporter):
        self.assertTrue(
            exporter.process.waitForFinished(2_000)
        )
        self.application.processEvents()

    def test_reports_a_successful_export(self):
        statuses = []
        output_paths = []

        exporter = TrimProjectExporter(
            executable="/bin/true"
        )
        exporter.status_changed.connect(
            statuses.append
        )
        exporter.succeeded.connect(
            output_paths.append
        )

        exporter.start(
            "project.json",
            "movie.mkv"
        )

        self.assertEqual(
            exporter.process.arguments(),
            [
                "export",
                "project.json",
                "--output",
                "movie.mkv"
            ]
        )

        self.wait_for_export(exporter)

        self.assertEqual(
            statuses,
            ["running", "succeeded"]
        )
        self.assertEqual(
            output_paths,
            ["movie.mkv"]
        )
        self.assertFalse(exporter.is_running)

    def test_reports_a_failed_export(self):
        statuses = []
        errors = []

        exporter = TrimProjectExporter(
            executable="/bin/false"
        )
        exporter.status_changed.connect(
            statuses.append
        )
        exporter.failed.connect(
            errors.append
        )

        exporter.start(
            Path("project.json"),
            Path("movie.mkv")
        )

        self.wait_for_export(exporter)

        self.assertEqual(
            statuses,
            ["running", "failed"]
        )
        self.assertEqual(
            errors,
            ["export failed (exit 1)"]
        )
        self.assertFalse(exporter.is_running)


if __name__ == "__main__":
    unittest.main()
