import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from video_encoder_ui.application import (
    load_startup_selection,
    select_media_path,
    select_project_path,
    select_source_path,
)

try:
    import mlt7
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        load_startup_selection,
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

    def test_keeps_a_video_as_a_fresh_session(self):
        source_path, session, project_path = (
            load_startup_selection(
                Path("/recordings/movie.m2t")
            )
        )

        self.assertEqual(
            source_path,
            Path("/recordings/movie.m2t")
        )
        self.assertIsNone(session)
        self.assertIsNone(project_path)

    def test_loads_a_single_source_project(self):
        reader = Mock()
        session = Mock()
        source = Mock(
            path=Path("/recordings/movie.m2t")
        )
        session.sources = (source,)
        reader.load.return_value = session

        source_path, restored, project_path = (
            load_startup_selection(
                Path("/projects/movie.json"),
                reader=reader
            )
        )

        reader.load.assert_called_once_with(
            Path("/projects/movie.json")
        )
        self.assertEqual(
            source_path,
            Path("/recordings/movie.m2t")
        )
        self.assertIs(restored, session)
        self.assertEqual(
            project_path,
            Path("/projects/movie.json")
        )

    def test_rejects_a_multi_source_project(self):
        reader = Mock()
        session = Mock()
        session.sources = (Mock(), Mock())
        reader.load.return_value = session

        with self.assertRaisesRegex(
            ValueError,
            "single-source projects only"
        ):
            load_startup_selection(
                Path("/projects/movie.json"),
                reader=reader
            )

    def test_selects_a_new_media_source(self):
        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getOpenFileName",
            return_value=(
                "/recordings/movie.m2t",
                "Fichiers vidéo",
            ),
        ) as dialog:
            selected_path = select_media_path()

        self.assertEqual(
            selected_path,
            Path("/recordings/movie.m2t")
        )
        dialog.assert_called_once()
        self.assertEqual(
            dialog.call_args.args[1],
            "Nouveau montage"
        )

    def test_selects_an_existing_project(self):
        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getOpenFileName",
            return_value=(
                "/projects/movie.json",
                "Projets de montage",
            ),
        ) as dialog:
            selected_path = select_project_path()

        self.assertEqual(
            selected_path,
            Path("/projects/movie.json")
        )
        dialog.assert_called_once()
        self.assertEqual(
            dialog.call_args.args[1],
            "Ouvrir un projet de découpage"
        )

if __name__ == "__main__":
    unittest.main()
