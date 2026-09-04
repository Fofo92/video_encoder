import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        MltFrameMonitor,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class ApplicationSegmentsTest(unittest.TestCase):
    def make_monitor(self):
        trim_session = SimpleNamespace(
            segments=(object(), object()),
            clear_segments=Mock(),
        )

        return SimpleNamespace(
            export_status="idle",
            trim_session=trim_session,
            clear_active_markers=Mock(),
            refresh_segment_list=Mock(),
        )

    def test_clears_all_segments_after_confirmation(self):
        monitor = self.make_monitor()

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.Yes
            ),
        ):
            MltFrameMonitor.clear_all_segments(
                monitor
            )

        monitor.trim_session.clear_segments.assert_called_once_with()
        monitor.clear_active_markers.assert_called_once_with()
        monitor.refresh_segment_list.assert_called_once_with()

    def test_keeps_segments_when_confirmation_is_declined(self):
        monitor = self.make_monitor()

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            return_value=(
                QtWidgets.QMessageBox.StandardButton.No
            ),
        ):
            MltFrameMonitor.clear_all_segments(
                monitor
            )

        monitor.trim_session.clear_segments.assert_not_called()
        monitor.clear_active_markers.assert_not_called()
        monitor.refresh_segment_list.assert_not_called()


if __name__ == "__main__":
    unittest.main()
