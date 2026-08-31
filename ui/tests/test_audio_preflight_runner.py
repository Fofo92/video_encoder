import tempfile
import unittest
from pathlib import Path

try:
    from PySide6 import QtCore
except ModuleNotFoundError:
    QtCore = None

if QtCore is not None:
    from video_encoder_ui.audio_preflight_runner import (
        AudioPreflightRunner,
    )


@unittest.skipIf(
    QtCore is None,
    "PySide6 is unavailable"
)
class AudioPreflightRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtCore.QCoreApplication.instance()
            or QtCore.QCoreApplication([])
        )

    def test_launches_preflight_and_returns_the_report(self):
        statuses = []
        reports = []
        errors = []

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "fake_preflight"
            executable.write_text(
                "#!/bin/sh\n"
                "printf '%s\\n' "
                "'{\"version\":1,\"audio_checks\":[]}'\n",
                encoding="utf-8"
            )
            executable.chmod(0o755)

            runner = AudioPreflightRunner(
                executable=executable
            )
            runner.status_changed.connect(statuses.append)
            runner.succeeded.connect(reports.append)
            runner.failed.connect(errors.append)

            runner.start(Path("mon montage.json"))

            self.assertTrue(
                runner.process.waitForFinished(2_000)
            )
            self.application.processEvents()

            self.assertEqual(
                runner.process.arguments(),
                ["preflight-audio", "mon montage.json"]
            )
            self.assertFalse(runner.is_running)

        self.assertEqual(
            statuses,
            ["running", "succeeded"]
        )
        self.assertEqual(
            reports,
            [{"version": 1, "audio_checks": []}]
        )
        self.assertEqual(errors, [])

    def test_reports_a_failed_preflight(self):
        statuses = []
        reports = []
        errors = []

        runner = AudioPreflightRunner(
            executable="/bin/false"
        )
        runner.status_changed.connect(statuses.append)
        runner.succeeded.connect(reports.append)
        runner.failed.connect(errors.append)

        runner.start(Path("mon montage.json"))

        self.assertTrue(
            runner.process.waitForFinished(2_000)
        )
        self.application.processEvents()

        self.assertEqual(
            statuses,
            ["running", "failed"]
        )
        self.assertEqual(reports, [])
        self.assertEqual(
            errors,
            ["audio preflight failed (exit 1)"]
        )
        self.assertFalse(runner.is_running)

    def test_rejects_invalid_or_unsupported_reports(self):
        payloads = [
            "",
            "not JSON",
            "[]",
            '{"version":2,"audio_checks":[]}',
            '{"version":true,"audio_checks":[]}',
            '{"version":1,"audio_checks":{}}',
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                statuses = []
                reports = []
                errors = []

                with tempfile.TemporaryDirectory() as directory:
                    executable = Path(directory) / "fake_preflight"
                    executable.write_text(
                        "#!/bin/sh\n"
                        "printf '%s\\n' '"
                        + payload
                        + "'\n",
                        encoding="utf-8"
                    )
                    executable.chmod(0o755)

                    runner = AudioPreflightRunner(
                        executable=executable
                    )
                    runner.status_changed.connect(statuses.append)
                    runner.succeeded.connect(reports.append)
                    runner.failed.connect(errors.append)

                    runner.start("project.json")

                    self.assertTrue(
                        runner.process.waitForFinished(2_000)
                    )
                    self.application.processEvents()

                    self.assertFalse(runner.is_running)

                self.assertEqual(
                    statuses,
                    ["running", "failed"]
                )
                self.assertEqual(reports, [])
                self.assertEqual(len(errors), 1)
                self.assertTrue(errors[0])

    def test_cancels_a_running_preflight(self):
        statuses = []
        reports = []
        errors = []

        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "slow_preflight"
            executable.write_text(
                "#!/bin/sh\n"
                "exec sleep 30\n",
                encoding="utf-8"
            )
            executable.chmod(0o755)

            runner = AudioPreflightRunner(
                executable=executable
            )
            runner.status_changed.connect(statuses.append)
            runner.succeeded.connect(reports.append)
            runner.failed.connect(errors.append)

            runner.start("project.json")

            try:
                self.assertTrue(
                    runner.process.waitForStarted(2_000)
                )
                self.assertTrue(runner.cancel())

                if runner.is_running:
                    self.assertTrue(
                        runner.process.waitForFinished(2_000)
                    )

                self.application.processEvents()

                self.assertFalse(runner.is_running)
                self.assertEqual(
                    statuses,
                    ["running", "cancelled"]
                )
                self.assertEqual(reports, [])
                self.assertEqual(errors, [])
            finally:
                if runner.is_running:
                    runner.process.kill()
                    runner.process.waitForFinished(2_000)

    def test_reports_a_missing_executable(self):
        statuses = []
        reports = []
        errors = []

        with tempfile.TemporaryDirectory() as directory:
            runner = AudioPreflightRunner(
                executable=Path(directory) / "missing_preflight"
            )
            runner.status_changed.connect(statuses.append)
            runner.succeeded.connect(reports.append)
            runner.failed.connect(errors.append)

            runner.start("project.json")

            self.assertFalse(
                runner.process.waitForStarted(2_000)
            )
            self.application.processEvents()

            self.assertFalse(runner.is_running)

        self.assertEqual(
            statuses,
            ["running", "failed"]
        )
        self.assertEqual(reports, [])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0])

if __name__ == "__main__":
    unittest.main()
