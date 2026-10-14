import unittest

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ModuleNotFoundError:
    QtCore = None
    QtGui = None
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.widgets import (
        ClickableSlider,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class ClickableSliderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtWidgets.QApplication.instance()
            or QtWidgets.QApplication([])
        )

    def test_retains_source_colors_for_segments_and_selection(self):
        slider = ClickableSlider(
            QtCore.Qt.Orientation.Horizontal
        )

        segments = (
            (10, 20, "#3daee9"),
            (30, 40, "#e6a23c"),
        )

        slider.set_segments(
            segments,
            selection_color="#67c23a"
        )

        self.assertEqual(
            slider.segments,
            segments
        )
        self.assertEqual(
            slider.selection_color,
            QtGui.QColor("#67c23a")
        )

    def test_cursor_turns_red_only_at_exact_marker_or_segment_bounds(self):
        slider = ClickableSlider(QtCore.Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.set_segments(((10, 20, "#3daee9"),))
        slider.set_markers(30, 40)
        for position in [10, 20, 30, 40]:
            slider.setValue(position)
            self.assertEqual(slider.position_color(), QtGui.QColor(210, 70, 60))
        for position in [9, 11, 19, 21, 31]:
            slider.setValue(position)
            self.assertEqual(slider.position_color(), QtGui.QColor(35, 95, 155))


if __name__ == "__main__":
    unittest.main()
