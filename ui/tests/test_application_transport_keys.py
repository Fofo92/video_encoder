import unittest
from types import SimpleNamespace
from unittest.mock import Mock

try:
    import mlt7
    from PySide6 import QtCore, QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import MltFrameMonitor


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 or MLT is unavailable"
)
class ApplicationTransportKeysTest(unittest.TestCase):
    def make_monitor(self):
        return SimpleNamespace(
            trim_project_exporter=Mock(
                is_running=False
            ),
            set_in_marker=Mock(),
            set_out_marker=Mock(),
            add_current_segment=Mock(),
            accelerate_backward=Mock(),
            pause_transport=Mock(),
            accelerate_forward=Mock(),
            show_previous_frame=Mock(),
            show_next_frame=Mock(),
        )

    def press(self, monitor, key):
        event = Mock()
        event.isAutoRepeat.return_value = False
        event.key.return_value = key

        MltFrameMonitor.keyPressEvent(
            monitor,
            event
        )

        event.accept.assert_called_once()

    def test_left_arrow_shows_the_previous_frame(self):
        monitor = self.make_monitor()

        self.press(
            monitor,
            QtCore.Qt.Key.Key_Left
        )

        monitor.show_previous_frame.assert_called_once_with()
        monitor.show_next_frame.assert_not_called()

    def test_right_arrow_shows_the_next_frame(self):
        monitor = self.make_monitor()

        self.press(
            monitor,
            QtCore.Qt.Key.Key_Right
        )

        monitor.show_next_frame.assert_called_once_with()
        monitor.show_previous_frame.assert_not_called()


if __name__ == "__main__":
    unittest.main()
