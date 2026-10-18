import tempfile
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

try:
    from video_encoder_ui.application import MltFrameMonitor
except ModuleNotFoundError:
    MltFrameMonitor = None

from video_encoder_ui.trim_session import SourceReference, TrimSession, SegmentSelection


@unittest.skipIf(MltFrameMonitor is None, "PySide6 or MLT is unavailable")
class ApplicationAdAnalysisSegmentTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        source = self.root / "9-1-1 - S04 E05 - Suis ta route.m2t"
        session = TrimSession()
        session.add_source(SourceReference("source", source))
        self.monitor = SimpleNamespace(
            source_path=source, source_id="source", trim_session=session,
            frame_source=SimpleNamespace(length=10000, frame_rate_numerator=25, frame_rate_denominator=1),
            in_position=100, out_position=9000, export_status="idle",
            ad_analysis_runner=Mock(), ad_trim_proposal_runner=Mock(), ad_trim_proposal_failed=Mock(),
            set_project_modified=Mock(), refresh_segment_list=Mock(), clear_active_markers=Mock(),
        )
        self.monitor.export_status_changed = Mock(side_effect=lambda state: setattr(self.monitor, "export_status", state))
        self.monitor.propose_ad_trim_from_report = MethodType(MltFrameMonitor.propose_ad_trim_from_report, self.monitor)

    def add_segment_and_clear_markers(self):
        def clear():
            self.monitor.in_position = None
            self.monitor.out_position = None
        self.monitor.clear_active_markers.side_effect = clear
        MltFrameMonitor.add_current_segment(self.monitor)
        self.assertIsNone(self.monitor.in_position)

    def test_source_markers_add_segment_analyze_and_load_proposal_keep_the_same_bounds(self):
        self.add_segment_and_clear_markers()
        with patch("video_encoder_ui.application.QtWidgets.QFileDialog.getExistingDirectory", return_value=str(self.root)):
            MltFrameMonitor.analyze_ads(self.monitor)
        arguments = self.monitor.ad_analysis_runner.start.call_args.args
        self.assertEqual(arguments[0], self.monitor.source_path)
        self.assertEqual(arguments[2:], (100, 9000))
        report = self.root / "boundary-hypotheses.json"
        MltFrameMonitor.ad_analysis_succeeded(self.monitor, {"report": report})
        self.monitor.ad_trim_proposal_runner.start.assert_called_once_with(report, self.monitor.source_path, 100, 9000)
        self.assertEqual(self.monitor.trim_session.segments, (SegmentSelection("source", 100, 9000),))

    def test_loading_an_existing_report_also_uses_the_saved_segment(self):
        self.add_segment_and_clear_markers()
        with patch("video_encoder_ui.application.QtWidgets.QFileDialog.getOpenFileName", return_value=("/report.json", "")):
            MltFrameMonitor.propose_ad_trim(self.monitor)
        self.monitor.ad_trim_proposal_runner.start.assert_called_once_with("/report.json", self.monitor.source_path, 100, 9000)

    def test_several_segments_do_not_launch_an_analysis_without_explicit_markers(self):
        self.add_segment_and_clear_markers()
        self.monitor.trim_session.add_segment(SegmentSelection("source", 9100, 9500))
        with patch("video_encoder_ui.application.QtWidgets.QMessageBox.information") as message:
            MltFrameMonitor.analyze_ads(self.monitor)
        message.assert_called_once()
        self.monitor.ad_analysis_runner.start.assert_not_called()
        self.assertEqual(len(self.monitor.trim_session.segments), 2)


if __name__ == "__main__":
    unittest.main()
