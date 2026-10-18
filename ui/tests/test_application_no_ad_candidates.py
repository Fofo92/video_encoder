import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
    from video_encoder_ui.application import MltFrameMonitor
except ModuleNotFoundError:
    MltFrameMonitor = None

from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter
from video_encoder_ui.trim_session import SourceReference, TrimSession, SegmentSelection


@unittest.skipIf(MltFrameMonitor is None, "PySide6 or MLT is unavailable")
class ApplicationNoAdCandidatesTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "Braveheart.m2t"
        self.source.write_bytes(b"capture")
        fingerprint = hashlib.sha256(str(self.source.resolve()).encode()).hexdigest()[:12]
        self.workspace = self.root / f"ad-analysis-{fingerprint}"
        (self.workspace / "detection").mkdir(parents=True)
        self.report = self.workspace / "detection" / "pub-candidates.json"
        self.report.write_text(json.dumps({
            "format": "video_encoder.6ter_pub_candidates", "version": 3,
            "source": str(self.source), "complete": True, "ffmpeg_exit_status": 0,
            "candidate_count": 0, "candidates": [], "analysed_samples": 24000,
        }))
        session = TrimSession()
        session.add_source(SourceReference("current", self.source))
        session.add_segment(SegmentSelection("current", 0, 99))
        self.monitor = SimpleNamespace(
            source_path=self.source, source_id="current", trim_session=session,
            frame_source=SimpleNamespace(length=10000, frame_rate_numerator=25, frame_rate_denominator=1),
            in_position=100, out_position=9000, export_status="idle", project_path=None,
            ad_analysis_runner=Mock(), ad_trim_proposal_failed=Mock(),
            clear_active_markers=Mock(), set_project_modified=Mock(), refresh_segment_list=Mock(),
            export_status_changed=Mock(), statusBar=Mock(return_value=Mock()), propose_ad_trim_from_report=Mock(),
        )
        self.monitor.ad_analysis_no_candidates = MethodType(MltFrameMonitor.ad_analysis_no_candidates, self.monitor)
        self.monitor.ad_trim_proposal_succeeded = MethodType(MltFrameMonitor.ad_trim_proposal_succeeded, self.monitor)

    def analyze(self, answer):
        with patch("video_encoder_ui.application.QtWidgets.QFileDialog.getExistingDirectory", return_value=str(self.root)), \
                patch("video_encoder_ui.application.QtWidgets.QMessageBox.question", return_value=answer) as question:
            MltFrameMonitor.analyze_ads(self.monitor)
        return question

    def test_reuses_the_existing_scan_and_offers_an_uncut_manual_montage_without_rescanning(self):
        question = self.analyze(QtWidgets.QMessageBox.StandardButton.Yes)
        self.monitor.ad_analysis_runner.start.assert_not_called()
        self.monitor.propose_ad_trim_from_report.assert_not_called()
        self.assertIn("ne garantit pas", question.call_args.args[2])
        self.assertIn("6ter", question.call_args.args[2])
        self.assertEqual(self.monitor.trim_session.segments, (SegmentSelection("current", 100, 9000),))
        self.assertEqual(len(self.monitor.trim_session.analysis_workspaces), 1)
        self.assertTrue(self.workspace.exists())
        document = {
            "format": "video_encoder.trim_project", "version": 2,
            "sources": [{"id": "current", "path": str(self.source)}],
            "timeline": [{"type": "segment", "source_id": "current", "start_frame": 100, "end_frame": 9000}],
        }
        writer = TrimProjectFileWriter(Mock(convert=Mock(return_value=document)))
        project = self.root / "Braveheart.json"
        writer.save(self.monitor.trim_session, project)
        self.assertFalse(self.workspace.exists())
        self.assertTrue(self.source.exists())
        self.assertEqual(json.loads(project.read_text()), document)

    def test_declining_keeps_the_existing_montage_and_diagnostics(self):
        segments = self.monitor.trim_session.segments
        self.analyze(QtWidgets.QMessageBox.StandardButton.No)
        self.assertEqual(self.monitor.trim_session.segments, segments)
        self.assertTrue(self.report.exists())
        self.monitor.ad_analysis_runner.start.assert_not_called()
        self.monitor.set_project_modified.assert_not_called()

    def test_newly_completed_empty_scan_uses_the_same_review_instead_of_loading_a_boundary_report(self):
        with patch("video_encoder_ui.application.QtWidgets.QMessageBox.question",
                   return_value=QtWidgets.QMessageBox.StandardButton.No):
            MltFrameMonitor.ad_analysis_succeeded(self.monitor, {"status": "no_candidates", "report": self.report})
        self.monitor.propose_ad_trim_from_report.assert_not_called()
        self.monitor.set_project_modified.assert_not_called()
