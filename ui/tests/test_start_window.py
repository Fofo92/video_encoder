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

    def test_main_toolbar_is_available_without_a_selected_job(self):
        self.window.resize(1130, 665)
        self.window.show()
        self.application.processEvents()
        self.assertTrue(self.window.main_toolbar.isVisible())
        self.assertFalse(self.window.menu_bar.isNativeMenuBar())
        self.assertFalse(self.window.exit_menu_bar.isNativeMenuBar())
        self.assertIs(self.window.layout().itemAt(0).widget(), self.window.main_toolbar)
        for action in (self.window.new_montage_action, self.window.open_project_action,
                       self.window.relocate_project_action, self.window.quarantine_action):
            self.assertIn(action, self.window.main_toolbar.actions())
            self.assertTrue(self.window.main_toolbar.widgetForAction(action).isVisible())
            self.assertFalse(action.icon().isNull())

    def test_main_toolbar_uses_the_same_actions_as_the_menus(self):
        requested = Mock()
        self.window.new_project_requested.connect(requested)
        button = self.window.main_toolbar.widgetForAction(self.window.new_montage_action)
        button.click()
        requested.assert_called_once_with()
        self.window.quarantine_action.setEnabled(False)
        self.assertFalse(self.window.main_toolbar.widgetForAction(self.window.quarantine_action).isEnabled())

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
            "Mettre des sources en quarantaine…"
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
    def test_home_actions_are_owned_by_the_home_window_not_temporary_menus(self):
        for name in ("new_project_action", "open_project_action", "quarantine_action", "relocate_project_action"):
            self.assertIs(self.window, getattr(self.window, name).parent())

    def test_rebuilding_a_menu_does_not_destroy_actions_used_when_opening_an_editor(self):
        from video_encoder_ui.editor_window_controller import EditorWindowController

        import gc

        gc.collect()
        self.application.processEvents()
        menu = self.window.home_menus[0]
        self.assertIs(menu.parent(), self.window.menu_bar)
        self.assertIs(self.window.menu_bar.actions()[0].menu(), menu)
        actions = menu.actions()
        menu.clear()
        for action in actions:
            menu.addAction(action)
        editor = QtWidgets.QWidget()
        self.addCleanup(editor.close)
        self.addCleanup(editor.deleteLater)
        controller = EditorWindowController(self.window, lambda _path: editor)
        controller.open("/videos/test.json")
        self.assertFalse(self.window.quarantine_action.isEnabled())
        self.assertFalse(self.window.relocate_project_action.isEnabled())
        controller.editor_closed()
        self.assertTrue(self.window.quarantine_action.isEnabled())
        self.assertTrue(self.window.relocate_project_action.isEnabled())


if __name__ == "__main__":
    unittest.main()
