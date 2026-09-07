import unittest
from pathlib import Path
from unittest.mock import Mock

from video_encoder_ui.application_controller import (
    ApplicationController,
)


class ApplicationControllerTest(unittest.TestCase):
    def setUp(self):
        self.start_window = Mock()
        self.start_controller = Mock()
        self.start_controller_class = Mock(
            return_value=self.start_controller
        )
        self.select_source = Mock()
        self.select_project = Mock()
        self.open_editor = Mock()
        self.queue_controller = Mock()
        self.quarantine_controller = Mock()

        self.controller = ApplicationController(
            start_window=self.start_window,
            select_source=self.select_source,
            select_project=self.select_project,
            open_editor=self.open_editor,
            queue_controller=self.queue_controller,
            quarantine_controller=(
                self.quarantine_controller
            ),
            start_controller_class=(
                self.start_controller_class
            ),
        )

    def test_opens_a_new_project_from_a_source(self):
        source_path = Path(
            "/recordings/movie.m2t"
        )
        self.select_source.return_value = (
            source_path
        )

        self.controller.new_project()

        self.open_editor.assert_called_once_with(
            source_path
        )

    def test_opens_an_existing_project(self):
        project_path = Path(
            "/projects/movie.json"
        )
        self.select_project.return_value = (
            project_path
        )

        self.controller.open_project()

        self.open_editor.assert_called_once_with(
            project_path
        )

    def test_does_nothing_when_selection_is_cancelled(
        self
    ):
        self.select_source.return_value = None
        self.select_project.return_value = None

        self.controller.new_project()
        self.controller.open_project()

        self.open_editor.assert_not_called()

    def test_displays_the_queue(self):
        self.controller.show_queue()

        self.queue_controller.show.assert_called_once_with()

    def test_quarantines_a_source(self):
        self.controller.quarantine_source()

        self.quarantine_controller.run.assert_called_once_with()

    def test_shows_the_start_window(self):
        self.controller.show()

        self.start_controller.show.assert_called_once_with()

if __name__ == "__main__":
    unittest.main()
