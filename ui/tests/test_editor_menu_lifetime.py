import gc
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7
    from PySide6 import QtCore, QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest("PySide6 or MLT is unavailable")

from video_encoder_ui.application import MltFrameMonitor
from video_encoder_ui.source_completion_controller import SourceCompletionController
from video_encoder_ui.start_window import StartWindow


class EditorMenuLifetimeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_editor_keeps_explicitly_parented_menus_alive_during_startup_wiring(self):
        source = SimpleNamespace(frames_per_second=25, length=10000, close=Mock())
        with patch('video_encoder_ui.application.MltFrameSource', return_value=source), \
                patch('video_encoder_ui.application.MltAudioPlayer'):
            window = MltFrameMonitor('/source.m2t')
        home = StartWindow()
        self.addCleanup(home.deleteLater)
        self.addCleanup(home.close)
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.close)
        self.addCleanup(window.shutdown)
        gc.collect()
        self.app.processEvents()
        self.assertEqual(['&Sources', '&Projets', '&Montage'], [menu.title() for menu in window.editor_menus])
        for menu in window.editor_menus:
            self.assertIs(window.editor_menu_bar, menu.parent())
            self.assertIn(menu.menuAction(), window.editor_menu_bar.actions())
        completion = SourceCompletionController(home, Mock(), Mock())
        completion.install_menu_bar(window.editor_menu_bar)
        window.projects_menu.addAction(home.delete_project_action)
        window.projects_menu.addAction(home.project_trash_action)
        gc.collect()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertIn(home.delete_project_action, window.projects_menu.actions())
        self.assertIn(home.project_trash_action, window.projects_menu.actions())
        self.assertIn('Vérifier les sources avant quarantaine…',
                      [action.text() for action in window.sources_menu.actions()])
        self.assertFalse(window.editor_menu_bar.isNativeMenuBar())
