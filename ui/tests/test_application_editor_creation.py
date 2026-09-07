import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    import mlt7
    from PySide6 import QtCore, QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        create_editor_window,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 or MLT is unavailable"
)
class ApplicationEditorCreationTest(
    unittest.TestCase
):
    def test_creates_an_editor_for_a_media_file(self):
        selected_path = Path(
            "/recordings/movie.m2t"
        )
        editor = Mock()
        editor_class = Mock(
            return_value=editor
        )

        with (
            patch.object(
                Path,
                "is_file",
                return_value=True,
            ),
            patch(
                "video_encoder_ui.application."
                "QtCore.QTimer.singleShot"
            ) as single_shot,
        ):
            created = create_editor_window(
                selected_path,
                editor_class=editor_class,
            )

        editor_class.assert_called_once_with(
            selected_path,
            trim_session=None,
            project_path=None,
        )
        editor.setAttribute.assert_called_once_with(
            QtCore.Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )

        single_shot.assert_called_once()
        self.assertIs(created, editor)

    def test_rejects_a_missing_selected_file(self):
        selected_path = Path(
            "/recordings/missing.m2t"
        )
        editor_class = Mock()

        with (
            patch.object(
                Path,
                "is_file",
                return_value=False,
            ),
            patch(
                "video_encoder_ui.application."
                "QtWidgets.QMessageBox.critical"
            ) as critical,
        ):
            created = create_editor_window(
                selected_path,
                editor_class=editor_class,
            )

        self.assertIsNone(created)
        editor_class.assert_not_called()
        critical.assert_called_once_with(
            None,
            "Fichier introuvable",
            (
                "Fichier introuvable : "
                "/recordings/missing.m2t"
            ),
        )


if __name__ == "__main__":
    unittest.main()
