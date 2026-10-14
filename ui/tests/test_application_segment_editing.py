import unittest
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
class ApplicationSegmentEditingTest(unittest.TestCase):
    def make_monitor(self):
        session = TrimSession()
        session.add_source(SourceReference("source", "/capture.m2t"))
        for a, b in [(0, 100), (200, 300), (400, 500)]:
            session.add_segment(SegmentSelection("source", a, b))
        return SimpleNamespace(
            export_status="idle", source_id="source", trim_session=session,
            segment_list=SimpleNamespace(currentRow=Mock(return_value=1), selectedItems=Mock(return_value=[object()])),
            in_position=None, out_position=None,
            position_slider=Mock(), in_marker_label=Mock(), out_marker_label=Mock(),
            add_segment_button=Mock(), show_frame=Mock(), timecode_for=str,
            set_project_modified=Mock(), refresh_segment_list=Mock(), clear_active_markers=Mock(),
        )

    def test_loads_bounds_then_replaces_selected_segment_in_place(self):
        monitor = self.make_monitor()
        originals = monitor.trim_session.segments
        MltFrameMonitor.edit_selected_segment(monitor)
        self.assertEqual((monitor.in_position, monitor.out_position), (200, 300))
        monitor.in_position, monitor.out_position = 210, 290
        MltFrameMonitor.add_current_segment(monitor)
        self.assertEqual(monitor.trim_session.segments, (
            originals[0], SegmentSelection("source", 210, 290), originals[2],
        ))
        monitor.set_project_modified.assert_called_once_with()

    def test_refuses_stale_selection_after_a_segment_was_deleted(self):
        monitor = self.make_monitor()
        MltFrameMonitor.edit_selected_segment(monitor)
        monitor.trim_session.remove_segment(monitor.trim_session.segments[0])
        remaining = monitor.trim_session.segments
        with patch("video_encoder_ui.application.QtWidgets.QMessageBox.warning") as warning:
            MltFrameMonitor.add_current_segment(monitor)
        self.assertEqual(monitor.trim_session.segments, remaining)
        warning.assert_called_once()
        monitor.set_project_modified.assert_not_called()

    def test_refuses_editing_while_export_is_running(self):
        monitor = self.make_monitor()
        monitor.export_status = "running"
        MltFrameMonitor.edit_selected_segment(monitor)
        self.assertIsNone(monitor.in_position)
        monitor.show_frame.assert_not_called()

    def test_keeps_append_behavior_without_an_editing_selection(self):
        monitor = self.make_monitor()
        monitor.in_position, monitor.out_position = 600, 700
        MltFrameMonitor.add_current_segment(monitor)
        self.assertEqual(len(monitor.trim_session.segments), 4)
        self.assertEqual(monitor.trim_session.segments[-1], SegmentSelection("source", 600, 700))


if __name__ == "__main__":
    unittest.main()
