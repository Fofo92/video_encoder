import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest("PySide6 is unavailable")

from video_encoder_ui.editor_window_controller import EditorWindowController
from video_encoder_ui.application_controller import ApplicationController
from video_encoder_ui.start_window import StartWindow


class EditorOpeningFeedbackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_toolbar_selection_opens_and_presents_the_editor_after_the_home(self):
        home = StartWindow()
        editor = QtWidgets.QWidget()
        for widget in (home, editor):
            self.addCleanup(widget.deleteLater)
            self.addCleanup(widget.close)
        factory = Mock(return_value=editor)
        controller = EditorWindowController(home, factory)
        app_controller = ApplicationController(home, lambda: '/capture.m2t', Mock(), controller.open, Mock(), Mock())
        calls = Mock()
        with patch.object(home, 'show', side_effect=lambda: calls.home()), \
                patch.object(editor, 'show', side_effect=lambda: calls.editor()), \
                patch.object(editor, 'raise_', side_effect=lambda: calls.raise_editor()), \
                patch.object(editor, 'activateWindow', side_effect=lambda: calls.activate_editor()):
            home.main_toolbar.widgetForAction(home.new_montage_action).click()
        factory.assert_called_once_with('/capture.m2t')
        self.assertEqual(['home', 'editor', 'raise_editor', 'activate_editor'],
                         [call[0] for call in calls.mock_calls])
        self.assertIs(controller.editor_window, editor)
        self.assertIsNotNone(app_controller)

    def test_factory_exception_is_visible_and_identifies_the_selected_file(self):
        home = QtWidgets.QWidget()
        self.addCleanup(home.deleteLater)
        self.addCleanup(home.close)
        controller = EditorWindowController(home, Mock(side_effect=AttributeError('missing action')))
        with patch('logging.exception'), patch.object(QtWidgets.QMessageBox, 'critical') as message:
            controller.open('/capture.m2t')
        message.assert_called_once()
        self.assertIn('/capture.m2t', message.call_args.args[-1])
        self.assertIn('AttributeError', message.call_args.args[-1])
        self.assertIsNone(controller.editor_window)
