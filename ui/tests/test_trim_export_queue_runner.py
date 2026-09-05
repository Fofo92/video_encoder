import unittest

try:
    from PySide6 import QtCore, QtWidgets
except ModuleNotFoundError:
    QtCore = None
    QtWidgets = None

if QtCore is not None:
    from video_encoder_ui.trim_export_queue_runner import (
        TrimExportQueueRunner,
    )


@unittest.skipIf(
    QtCore is None,
    "PySide6 is unavailable",
)
class TrimExportQueueRunnerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtWidgets.QApplication.instance()
            or QtWidgets.QApplication([])
        )

    def test_starts_the_queue_with_sleep_inhibition(self):
        runner = TrimExportQueueRunner(
            executable="/app/video_encoder",
            inhibitor_executable="/usr/bin/systemd-inhibit",
            ccextractor_executable=(
                "/app/video_encoder_ccextractor"
            ),
        )

        runner.start()

        self.assertEqual(
            runner.process.program(),
            "/usr/bin/systemd-inhibit",
        )
        self.assertEqual(
            runner.process.arguments(),
            [
                "--what=sleep",
                "--who=video_encoder",
                "--why=File d’export video_encoder en cours",
                "--mode=block",
                "/app/video_encoder",
                "run-trim-exports",
                "--once",
            ],
        )
        self.assertEqual(
            runner.process.processEnvironment().value(
                "CCEXTRACTOR_EXECUTABLE"
            ),
            "/app/video_encoder_ccextractor",
        )

        runner.process.kill()
        self.wait_for_runner(runner)

    def wait_for_runner(self, runner):
        self.assertTrue(
            runner.process.waitForFinished(2_000)
        )
        self.application.processEvents()

    def test_reports_a_successful_queue_run(self):
        statuses = []
        succeeded = []

        runner = TrimExportQueueRunner(
            executable="/bin/true",
            ccextractor_executable="/bin/true",
        )
        runner.status_changed.connect(
            statuses.append
        )
        runner.succeeded.connect(
            lambda: succeeded.append(True)
        )

        runner.start()
        self.wait_for_runner(runner)

        self.assertEqual(
            runner.process.arguments(),
            [
                "run-trim-exports",
                "--once",
            ],
        )
        self.assertEqual(
            statuses,
            ["running", "succeeded"],
        )
        self.assertEqual(
            succeeded,
            [True],
        )
        self.assertFalse(runner.is_running)

    def test_reports_a_failed_queue_run(self):
        statuses = []
        errors = []

        runner = TrimExportQueueRunner(
            executable="/bin/false",
            ccextractor_executable="/bin/true",
        )
        runner.status_changed.connect(
            statuses.append
        )
        runner.failed.connect(
            errors.append
        )

        runner.start()
        self.wait_for_runner(runner)

        self.assertEqual(
            statuses,
            ["running", "failed"],
        )
        self.assertEqual(
            errors,
            [
                "trim export queue failed (exit 1)"
            ],
        )
        self.assertFalse(runner.is_running)

if __name__ == "__main__":
    unittest.main()
