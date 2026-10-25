import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.start_window import (
        StartWindow,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable"
)
class StartWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = (
            QtWidgets.QApplication.instance()
            or QtWidgets.QApplication([])
        )

    def setUp(self):
        self.window = StartWindow()

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def test_offers_the_main_startup_actions(self):
        self.assertEqual(
            self.window.windowTitle(),
            "video_encoder — Montages"
        )
        self.assertEqual(
            self.window.new_project_action.text(),
            "Ouvrir une source…"
        )
        self.assertEqual(
            self.window.open_project_action.text(),
            "Ouvrir un projet…"
        )
        self.assertEqual(self.window.tabs.count(), 8)
        self.assertFalse(hasattr(self.window, "queue_button"))

    def test_emits_the_selected_action(self):
        new_requested = Mock()
        open_requested = Mock()
        queue_requested = Mock()

        self.window.new_project_requested.connect(
            new_requested
        )
        self.window.open_project_requested.connect(
            open_requested
        )
        self.window.queue_requested.connect(
            queue_requested
        )

        self.window.new_project_action.trigger()
        self.window.open_project_action.trigger()


        new_requested.assert_called_once_with()
        open_requested.assert_called_once_with()
        queue_requested.assert_not_called()

    def test_requests_source_quarantine(self):
        quarantine_requested = Mock()

        self.window.quarantine_requested.connect(
            quarantine_requested
        )

        self.assertEqual(
            self.window.quarantine_action.text(),
            "Mettre une source en quarantaine…"
        )

        self.window.quarantine_action.trigger()

        quarantine_requested.assert_called_once_with()

    def test_keeps_editing_actions_available(self):
        self.assertTrue(
            self.window.new_project_action.isEnabled()
        )
        self.assertTrue(
            self.window.open_project_action.isEnabled()
        )

if __name__ == "__main__":
    unittest.main()
