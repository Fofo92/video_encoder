import unittest
import tempfile
from pathlib import Path

try:
    from PySide6 import QtCore
except ModuleNotFoundError:
    QtCore = None

if QtCore is not None:
    from video_encoder_ui.trim_project_exporter import (
        TrimProjectExporter,
    )

@unittest.skipIf(
    QtCore is None,
    "PySide6 is unavailable"
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

    def test_routes_warnings_separately_from_stages(self):
        warnings = []
        stages = []
        statuses = []

        exporter = TrimProjectExporter()

        exporter.warning_received.connect(
            warnings.append
        )
        exporter.stage_changed.connect(
            stages.append
        )
        exporter.status_changed.connect(
            statuses.append
        )

        warning = {
            "type": "warning",
            "code": "no_subtitles_found",
            "message": "Aucun sous-titre trouvé.",
            "group": 1
        }
        stage = {
            "stage": "subtitles",
            "step": 4,
            "total": 5
        }

        exporter.record_event_output(
            [stage, warning],
            []
        )

        self.assertEqual(warnings, [warning])
        self.assertEqual(stages, [stage])
        self.assertEqual(statuses, [])
        self.assertFalse(exporter.completed)

    def test_reports_mlt_progress(self):
        percentages = []

        with tempfile.TemporaryDirectory() as directory:
            executable = (
                Path(directory)
                / "progress_export"
            )
            executable.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' "
                "'Current Frame: 1, percentage: 1' "
                "'Current Frame: 2, percentage: 1' "
                "'Current Frame: 42, percentage: 42' "
                "'Current Frame: 100, percentage: 100' "
                ">&2\n",
                encoding="utf-8"
            )
            executable.chmod(0o755)

            exporter = TrimProjectExporter(
                executable=executable
            )
            exporter.progress_changed.connect(
                percentages.append
            )

            exporter.start(
                "project.json",
                "movie.mkv"
            )
            self.wait_for_export(exporter)

        self.assertEqual(
            percentages,
            [1, 42, 100]
        )
        self.assertEqual(
            exporter.standard_error,
            ""
        )

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

    def test_cancels_the_export_process_group(self):
        statuses = []

        with tempfile.TemporaryDirectory() as directory:
            executable = (
                Path(directory)
                / "slow_export"
            )
            executable.write_text(
                "#!/bin/sh\n"
                "sleep 30\n",
                encoding="utf-8"
            )
            executable.chmod(0o755)

            exporter = TrimProjectExporter(
                executable=executable
            )
            exporter.status_changed.connect(
                statuses.append
            )

            exporter.start(
                "project.json",
                "movie.mkv"
            )

            self.assertTrue(
                exporter.process.waitForStarted(2_000)
            )
            self.assertTrue(
                exporter.cancel()
            )

            self.application.processEvents()

        self.assertEqual(
            statuses,
            ["running", "cancelled"]
        )
        self.assertFalse(exporter.is_running)

    def test_reports_structured_export_stages(self):
        stages = []

        with tempfile.TemporaryDirectory() as directory:
            executable = (
                Path(directory)
                / "staged_export"
            )
            executable.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' "
                "'VIDEO_ENCODER_EXPORT_EVENT "
                "{\"stage\":\"video\","
                "\"step\":1,\"total\":4}'\n",
                encoding="utf-8"
            )
            executable.chmod(0o755)

            exporter = TrimProjectExporter(
                executable=executable
            )
            exporter.stage_changed.connect(
                stages.append
            )

            exporter.start(
                "project.json",
                "movie.mkv"
            )
            self.wait_for_export(exporter)

        self.assertEqual(
            stages,
            [
                {
                    "stage": "video",
                    "step": 1,
                    "total": 4
                }
            ]
        )

if __name__ == "__main__":
    unittest.main()
