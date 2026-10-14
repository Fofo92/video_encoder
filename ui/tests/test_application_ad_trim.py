import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession

if QtWidgets is not None:
    from video_encoder_ui.application import MltFrameMonitor


@unittest.skipIf(QtWidgets is None, "PySide6 is unavailable")
class ApplicationAdTrimTest(unittest.TestCase):
    def make_monitor(self):
        session = TrimSession()
        session.add_source(SourceReference("current", "/capture.m2t"))
        session.add_segment(SegmentSelection("current", 0, 99))
        return SimpleNamespace(
            source_path=Path("/capture.m2t"), source_id="current", trim_session=session,
            frame_source=SimpleNamespace(length=100, frame_rate_numerator=25, frame_rate_denominator=1),
            in_position=10, out_position=80, export_status="idle", project_path=Path("/original.json"),
            ad_trim_proposal_runner=Mock(), export_status_changed=Mock(),
            ad_trim_proposal_failed=Mock(), clear_active_markers=Mock(),
            set_project_modified=Mock(), refresh_segment_list=Mock(), statusBar=Mock(return_value=Mock()),
        )

    def test_requires_episode_bounds_without_changing_the_montage(self):
        monitor = self.make_monitor()
        monitor.in_position = None
        original = monitor.trim_session.segments
        with patch("video_encoder_ui.application.QtWidgets.QMessageBox.information"):
            MltFrameMonitor.propose_ad_trim(monitor)
        monitor.ad_trim_proposal_runner.start.assert_not_called()
        self.assertEqual(monitor.trim_session.segments, original)

    def test_passes_manual_bounds_and_current_source_to_the_backend(self):
        monitor = self.make_monitor()
        with patch("video_encoder_ui.application.QtWidgets.QFileDialog.getOpenFileName", return_value=("/report.json", "")):
            MltFrameMonitor.propose_ad_trim(monitor)
        monitor.ad_trim_proposal_runner.start.assert_called_once_with("/report.json", Path("/capture.m2t"), 10, 80)
        monitor.export_status_changed.assert_called_once_with("proposing")

    def test_cancelled_file_selection_leaves_the_montage_intact(self):
        monitor = self.make_monitor()
        original = monitor.trim_session.segments
        with patch("video_encoder_ui.application.QtWidgets.QFileDialog.getOpenFileName", return_value=("", "")):
            MltFrameMonitor.propose_ad_trim(monitor)
        self.assertEqual(monitor.trim_session.segments, original)
        monitor.export_status_changed.assert_not_called()

    def result(self, source="/capture.m2t", last=80):
        session = TrimSession()
        session.add_source(SourceReference("source", source))
        session.add_segment(SegmentSelection("source", 10, 19))
        session.add_segment(SegmentSelection("source", 30, last))
        return {"session": session, "summary": {}}

    def test_adopts_bounded_proposal_as_a_new_unsaved_project(self):
        monitor = self.make_monitor()
        MltFrameMonitor.ad_trim_proposal_succeeded(monitor, self.result())
        self.assertEqual([(s.source_id, s.start_frame, s.end_frame) for s in monitor.trim_session.segments],
                         [("current", 10, 19), ("current", 30, 80)])
        self.assertIsNone(monitor.project_path)
        monitor.set_project_modified.assert_called_once_with()
        monitor.export_status_changed.assert_called_once_with("idle")

    def test_wrong_source_or_out_of_range_proposal_preserves_previous_project(self):
        for result in [self.result(source="/other.m2t"), self.result(last=120)]:
            monitor = self.make_monitor()
            original = monitor.trim_session.segments
            MltFrameMonitor.ad_trim_proposal_succeeded(monitor, result)
            self.assertEqual(monitor.trim_session.segments, original)
            self.assertEqual(monitor.project_path, Path("/original.json"))
            monitor.ad_trim_proposal_failed.assert_called_once()


if __name__ == "__main__":
    unittest.main()
