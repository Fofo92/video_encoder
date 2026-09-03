import unittest

try:
    from PySide6 import QtGui, QtWidgets
except ModuleNotFoundError:
    QtGui = None
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.source_information_dialog import (
        SOURCE_COLORS,
        SourceInformationDialog,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class SourceInformationDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtWidgets.QApplication.instance()
            or QtWidgets.QApplication([])
        )

    def test_displays_one_colored_tab_per_source(self):
        sources = [
            {
                "path": "/commun/source-a.m2t",
                "inspection": {
                    "duration": 3600,
                    "size_bytes": 1073741824,
                    "video_tracks": [
                        {
                            "index": 0,
                            "codec": "h264",
                            "width": 1920,
                            "height": 1080,
                            "frame_rate": {
                                "numerator": 25,
                                "denominator": 1,
                            },
                        }
                    ],
                    "audio_tracks": [
                        {
                            "index": 1,
                            "codec": "eac3",
                            "language": "fra",
                            "default": True,
                            "visual_impaired": False,
                        }
                    ],
                    "subtitle_tracks": [],
                },
            },
            {
                "path": "/commun/source-c.m2t",
                "inspection": {
                    "duration": 600,
                },
            },
        ]

        dialog = SourceInformationDialog(sources)

        self.assertEqual(dialog.tabs.count(), 2)
        self.assertEqual(
            dialog.tabs.tabText(0),
            "source-a.m2t",
        )
        self.assertEqual(
            dialog.tabs.tabBar().tabTextColor(0),
            QtGui.QColor(SOURCE_COLORS[0]),
        )

        text = dialog.tabs.widget(0).toPlainText()

        self.assertIn(
            "Durée : 01:00:00.000",
            text,
        )
        self.assertIn(
            "Piste 0 — h264 — 1920×1080 — 25 i/s",
            text,
        )
        self.assertIn(
            "Piste 1 — eac3 — fra — par défaut",
            text,
        )


if __name__ == "__main__":
    unittest.main()
