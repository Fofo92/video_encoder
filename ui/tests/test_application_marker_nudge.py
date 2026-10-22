import unittest
from types import SimpleNamespace
from unittest.mock import Mock

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import MltFrameMonitor


@unittest.skipIf(QtWidgets is None, "PySide6 is unavailable")
class MarkerNudgeTest(unittest.TestCase):
    def monitor(self, index=1, first=10, last=20, status="idle"):
        return SimpleNamespace(
            export_status=status, frame_source=SimpleNamespace(length=100),
            in_position=first, out_position=last, editing_segment_index=0,
            nudge_marker_selector=SimpleNamespace(currentIndex=Mock(return_value=index)),
            position_slider=Mock(), in_marker_label=Mock(), out_marker_label=Mock(),
            timecode_for=str, show_frame=Mock(), statusBar=Mock(return_value=Mock()),
        )

    def test_adjusts_in_without_changing_out(self):
        monitor = self.monitor()
        MltFrameMonitor.nudge_marker(monitor, -1)
        self.assertEqual((monitor.in_position, monitor.out_position), (9, 20))
        monitor.show_frame.assert_called_once_with(9)
        monitor.position_slider.set_markers.assert_called_once_with(9, 20)

    def test_adjusts_out_without_changing_in(self):
        monitor = self.monitor(index=2)
        MltFrameMonitor.nudge_marker(monitor, 1)
        self.assertEqual((monitor.in_position, monitor.out_position), (10, 21))
        monitor.out_marker_label.setToolTip.assert_called_once_with("OUT : image 21")

    def test_preserves_minimum_two_image_segment(self):
        for index, delta in [(1, 1), (2, -1)]:
            monitor = self.monitor(index=index, first=10, last=11)
            MltFrameMonitor.nudge_marker(monitor, delta)
            self.assertEqual((monitor.in_position, monitor.out_position), (10, 11))
            monitor.show_frame.assert_not_called()

    def test_rejects_source_overflow(self):
        for index, delta in [(1, -1), (2, 1)]:
            monitor = self.monitor(index=index, first=0, last=99)
            MltFrameMonitor.nudge_marker(monitor, delta)
            self.assertEqual((monitor.in_position, monitor.out_position), (0, 99))

    def test_does_not_adjust_during_background_work(self):
        for status in ["running", "preflight", "confirming"]:
            monitor = self.monitor(status=status)
            MltFrameMonitor.nudge_marker(monitor, 1)
            self.assertEqual(monitor.in_position, 10)
            monitor.show_frame.assert_not_called()

    def test_missing_marker_does_not_modify_other_marker(self):
        monitor = self.monitor(first=None)
        MltFrameMonitor.nudge_marker(monitor, 1)
        self.assertEqual((monitor.in_position, monitor.out_position), (None, 20))
        monitor.show_frame.assert_not_called()

    def test_selector_previews_the_chosen_boundary(self):
        monitor = self.monitor(index=2)
        MltFrameMonitor.preview_nudge_marker(monitor, 1)
        monitor.show_frame.assert_called_once_with(20)


if __name__ == "__main__":
    unittest.main()
