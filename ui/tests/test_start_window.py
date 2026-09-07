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
        self.window.set_queue_running(False)
        self.window.close()
        self.window.deleteLater()

    def test_offers_the_main_startup_actions(self):
        self.assertEqual(
            self.window.windowTitle(),
            "video_encoder"
        )
        self.assertEqual(
            self.window.new_project_button.text(),
            "Nouveau montage…"
        )
        self.assertEqual(
            self.window.open_project_button.text(),
            "Ouvrir un projet de découpage…"
        )
        self.assertEqual(
            self.window.queue_button.text(),
            "File des montages…"
        )

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

        self.window.new_project_button.click()
        self.window.open_project_button.click()
        self.window.queue_button.click()

        new_requested.assert_called_once_with()
        open_requested.assert_called_once_with()
        queue_requested.assert_called_once_with()

    def test_disables_editing_while_queue_runs(self):
        self.window.set_queue_running(True)

        self.assertFalse(
            self.window.new_project_button.isEnabled()
        )
        self.assertFalse(
            self.window.open_project_button.isEnabled()
        )

        self.window.set_queue_running(False)

        self.assertTrue(
            self.window.new_project_button.isEnabled()
        )
        self.assertTrue(
            self.window.open_project_button.isEnabled()
        )

    def test_prevents_closing_while_queue_runs(self):
        event = Mock()
        self.window.set_queue_running(True)

        with patch(
            "video_encoder_ui.start_window."
            "QtWidgets.QMessageBox.information"
        ) as information:
            self.window.closeEvent(event)

        event.ignore.assert_called_once_with()
        information.assert_called_once_with(
            self.window,
            "File en cours",
            (
                "La file des montages est en cours "
                "d’exécution.\n"
                "Attends sa fin avant de fermer "
                "video_encoder."
            ),
        )

if __name__ == "__main__":
    unittest.main()
