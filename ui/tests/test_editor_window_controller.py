import unittest
from pathlib import Path
from unittest.mock import Mock

from video_encoder_ui.editor_window_controller import (
    EditorWindowController,
)


class EditorWindowControllerTest(
    unittest.TestCase
):
    def setUp(self):
        self.start_window = Mock()
        self.editor_window = Mock()
        self.editor_factory = Mock(
            return_value=self.editor_window
        )
        self.controller = EditorWindowController(
            start_window=self.start_window,
            editor_factory=self.editor_factory,
        )

    def test_opens_the_editor_and_hides_start(self):
        selected_path = Path(
            "/recordings/movie.m2t"
        )

        self.controller.open(selected_path)

        self.editor_factory.assert_called_once_with(
            selected_path
        )
        self.editor_window.show.assert_called_once_with()
        self.start_window.hide.assert_called_once_with()
        self.assertIs(
            self.controller.editor_window,
            self.editor_window,
        )
        self.editor_window.setAttribute.assert_called_once()

    def test_returns_to_start_when_editor_closes(
        self
    ):
        self.controller.editor_window = (
            self.editor_window
        )

        self.controller.editor_closed()

        self.assertIsNone(
            self.controller.editor_window
        )
        self.start_window.show.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
