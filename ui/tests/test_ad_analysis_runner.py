import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

try:
    from PySide6 import QtCore
except ModuleNotFoundError:
    QtCore = None

if QtCore is not None:
    from video_encoder_ui.ad_analysis_runner import AdAnalysisRunner


@unittest.skipIf(QtCore is None, "PySide6 is unavailable")
class AdAnalysisRunnerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name) / "source.m2t"
        self.source.write_bytes(b"sample")
        self.runner = AdAnalysisRunner()
        self.runner.process = Mock()
        self.runner.process.readAllStandardOutput.return_value = b""

    def test_starts_frozen_pipeline_without_export(self):
        workspace = Path(self.tmp.name) / "analysis"
        self.runner.start(self.source, workspace, 10, 80)
        command, args = self.runner.process.start.call_args.args
        self.assertEqual(command, "ruby")
        self.assertTrue(args[0].endswith("script/prepare_ad_trim.rb"))
        self.assertEqual(args[-4:], ["--start-frame", "10", "--end-frame", "80"])

    def test_refuses_to_overwrite_workspace(self):
        with self.assertRaises(FileExistsError):
            self.runner.start(self.source, self.source.parent, 10, 80)

    def test_failure_preserves_workspace(self):
        workspace = Path(self.tmp.name) / "analysis"
        self.runner.start(self.source, workspace, 10, 80)
        failed = Mock()
        self.runner.failed.connect(failed)
        self.runner.finish(1, QtCore.QProcess.ExitStatus.NormalExit)
        failed.assert_called_once()
        self.assertIn(str(workspace), failed.call_args.args[0])

    def test_success_requires_project_and_report(self):
        workspace = Path(self.tmp.name) / "analysis"
        self.runner.start(self.source, workspace, 10, 80)
        (workspace / "boundaries").mkdir(parents=True)
        (workspace / "boundaries" / "boundary-hypotheses.json").write_text("{}")
        (workspace / "proposal.json").write_text(json.dumps({"format": "video_encoder.trim_project"}))
        succeeded = Mock()
        self.runner.succeeded.connect(succeeded)
        self.runner.finish(0, QtCore.QProcess.ExitStatus.NormalExit)
        succeeded.assert_called_once()
        self.assertEqual(succeeded.call_args.args[0]["workspace"], workspace)

    def test_cancel_ignores_late_completion(self):
        self.runner.start(self.source, Path(self.tmp.name) / "analysis", 10, 80)
        failed = Mock()
        self.runner.failed.connect(failed)
        self.runner.cancel()
        self.runner.finish(1, QtCore.QProcess.ExitStatus.NormalExit)
        failed.assert_not_called()

    def test_zero_candidates_returns_a_reviewable_outcome_instead_of_a_refinement_error(self):
        workspace = Path(self.tmp.name) / "analysis"
        self.runner.start(self.source, workspace, 10, 80)
        (workspace / "detection").mkdir(parents=True)
        report = workspace / "detection" / "pub-candidates.json"
        report.write_text(json.dumps({
            "format": "video_encoder.6ter_pub_candidates", "version": 3,
            "source": str(self.source), "complete": True, "ffmpeg_exit_status": 0,
            "candidate_count": 0, "candidates": [], "analysed_samples": 1000,
        }))
        succeeded, failed = Mock(), Mock()
        self.runner.succeeded.connect(succeeded)
        self.runner.failed.connect(failed)
        self.runner.finish(0, QtCore.QProcess.ExitStatus.NormalExit)
        failed.assert_not_called()
        self.assertEqual(succeeded.call_args.args[0]["status"], "no_candidates")
        self.assertEqual(succeeded.call_args.args[0]["report"], report)
