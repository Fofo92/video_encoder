import unittest

try:
    from PySide6 import QtGui, QtWidgets
except ModuleNotFoundError:
    QtGui = None
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.segment_list import (
        SegmentListWidget,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class SegmentListWidgetTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtWidgets.QApplication.instance()
            or QtWidgets.QApplication([])
        )

    def test_colors_the_source_column(self):
        widget = SegmentListWidget()

        widget.set_rows(
            [
                (
                    1,
                    "source",
                    "00:00:01:00",
                    "00:00:02:00",
                    "00:00:01:01",
                ),
                (
                    2,
                    "source_1",
                    "00:00:03:00",
                    "00:00:04:00",
                    "00:00:01:01",
                ),
            ],
            source_colors={
                "source": "#3daee9",
                "source_1": "#e6a23c",
            },
        )

        first_source = widget.item(0, 1)
        second_source = widget.item(1, 1)

        self.assertEqual(
            first_source.foreground().color(),
            QtGui.QColor("#3daee9"),
        )
        self.assertEqual(
            second_source.foreground().color(),
            QtGui.QColor("#e6a23c"),
        )
        self.assertTrue(first_source.font().bold())
        self.assertTrue(second_source.font().bold())


if __name__ == "__main__":
    unittest.main()
