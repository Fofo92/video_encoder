import json
import unittest
from unittest.mock import Mock

try:
    from PySide6 import QtCore
except ModuleNotFoundError:
    QtCore = None

if QtCore is not None:
    from video_encoder_ui.ad_trim_proposal_runner import AdTrimProposalRunner


@unittest.skipIf(QtCore is None, "PySide6 is unavailable")
class AdTrimProposalRunnerTest(unittest.TestCase):
    def make_runner(self):
        runner = AdTrimProposalRunner()
        runner.process = Mock()
        runner.process.readAllStandardError.return_value = b""
        runner.process.readAllStandardOutput.return_value = b'{"segments": 1}'
        runner.start("/report.json", "/capture.m2t", 10, 80)
        self.addCleanup(runner.clean_up)
        return runner

    def test_reads_draft_then_cleans_temporary_files(self):
        runner = self.make_runner()
        project = runner.project
        project.write_text(json.dumps({
            "format": "video_encoder.trim_project", "version": 2,
            "sources": [{"id": "source", "path": "/capture.m2t"}],
            "timeline": [{"type": "segment", "source_id": "source", "start_frame": 10, "end_frame": 80}],
        }))
        success = Mock()
        runner.succeeded.connect(success)
        runner.finish(0, QtCore.QProcess.ExitStatus.NormalExit)
        success.assert_called_once()
        self.assertEqual(success.call_args.args[0]["session"].segments[0].end_frame, 80)
        self.assertIsNone(runner.directory)
        self.assertFalse(project.exists())

    def test_backend_error_cleans_up_and_returns_error(self):
        runner = self.make_runner()
        runner.process.readAllStandardError.return_value = b"wrong source"
        failed = Mock()
        runner.failed.connect(failed)
        runner.finish(1, QtCore.QProcess.ExitStatus.NormalExit)
        failed.assert_called_once_with("wrong source")
        self.assertIsNone(runner.directory)

    def test_cancellation_does_not_emit_a_late_error(self):
        runner = self.make_runner()
        failed = Mock()
        runner.failed.connect(failed)
        runner.cancel()
        runner.finish(1, QtCore.QProcess.ExitStatus.NormalExit)
        runner.process.terminate.assert_called_once()
        failed.assert_not_called()
        self.assertIsNone(runner.directory)

    def test_failed_start_cleans_up(self):
        runner = self.make_runner()
        runner.process.errorString.return_value = "ruby missing"
        failed = Mock()
        runner.failed.connect(failed)
        runner.process_error(QtCore.QProcess.ProcessError.FailedToStart)
        failed.assert_called_once_with("ruby missing")
        self.assertIsNone(runner.directory)


if __name__ == "__main__":
    unittest.main()
