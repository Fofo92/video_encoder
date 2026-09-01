import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import mlt7
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        select_source_path,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 or MLT is unavailable"
)
class ApplicationSourceSelectionTest(unittest.TestCase):
    def test_uses_the_source_argument(self):
        source = select_source_path(
            ["/recordings/movie.m2t"]
        )

        self.assertEqual(
            source,
            Path("/recordings/movie.m2t")
        )

    def test_asks_for_a_source_without_an_argument(self):
        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getOpenFileName",
            return_value=(
                "/recordings/movie.m2t",
                "Fichiers vidéo"
            ),
        ):
            source = select_source_path([])

        self.assertEqual(
            source,
            Path("/recordings/movie.m2t")
        )

    def test_returns_none_when_selection_is_cancelled(self):
        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ):
            source = select_source_path([])

        self.assertIsNone(source)


if __name__ == "__main__":
    unittest.main()
