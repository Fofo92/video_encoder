import unittest
from unittest.mock import Mock

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest("PySide6 is unavailable")

from video_encoder_ui.montage_toolbar import install_montage_toolbar


class MontageToolbarTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.window = QtWidgets.QMainWindow()
        self.names = (
            "new_montage_action", "save_project_action", "identify_vidb_action",
            "queue_export_action", "show_export_queue_action", "export_project_action",
            "cancel_export_action", "source_information_action",
        )
        for name in self.names:
            setattr(self.window, name, QtGui.QAction(name, self.window))
        self.window.cancel_export_action.setEnabled(False)
        self.toolbar = install_montage_toolbar(self.window)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()

    def test_lifecycle_order_uses_existing_actions_with_icons_only(self):
        actions = [action for action in self.toolbar.actions() if not action.isSeparator()]
        self.assertEqual([getattr(self.window, name) for name in self.names], actions)
        self.assertEqual(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly, self.toolbar.toolButtonStyle())
        self.assertEqual(3, sum(action.isSeparator() for action in self.toolbar.actions()))
        self.assertTrue(all(action.toolTip() for action in actions))

    def test_queue_button_invokes_the_existing_command_once(self):
        callback = Mock()
        self.window.queue_export_action.triggered.connect(callback)
        self.toolbar.widgetForAction(self.window.queue_export_action).click()
        callback.assert_called_once()

    def test_disabled_commands_remain_disabled_and_follow_the_action(self):
        action = self.window.cancel_export_action
        button = self.toolbar.widgetForAction(action)
        self.assertFalse(button.isEnabled())
        action.setEnabled(True)
        self.assertTrue(button.isEnabled())
        self.window.queue_export_action.setEnabled(False)
        self.assertFalse(self.toolbar.widgetForAction(self.window.queue_export_action).isEnabled())
