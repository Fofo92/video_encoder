import unittest
from unittest.mock import Mock

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.start_window import (
        StartWindow,
    )
    from video_encoder_ui.start_window_controller import (
        StartWindowController,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable"
)
class StartWindowControllerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtWidgets.QApplication.instance()
            or QtWidgets.QApplication([])
        )

    def setUp(self):
        self.window = StartWindow()
        self.new_project = Mock()
        self.open_project = Mock()
        self.show_queue = Mock()

        self.controller = StartWindowController(
            window=self.window,
            new_project=self.new_project,
            open_project=self.open_project,
            show_queue=self.show_queue,
        )

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def test_routes_the_startup_actions(self):
        self.window.new_project_button.click()
        self.window.open_project_button.click()
        self.window.queue_button.click()

        self.new_project.assert_called_once_with()
        self.open_project.assert_called_once_with()
        self.show_queue.assert_called_once_with()

    def test_shows_the_start_window(self):
        self.controller.show()

        self.assertTrue(
            self.window.isVisible()
        )


if __name__ == "__main__":
    unittest.main()
