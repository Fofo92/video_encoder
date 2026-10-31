import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest("PySide6 is unavailable")

from video_encoder_ui.start_window import StartWindow
from video_encoder_ui.project_removal_dialog import remove_project


class HomeMenuCoherenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_new_montage_has_one_menu_entry_and_deletion_stays_in_projects(self):
        window = StartWindow()
        self.addCleanup(window.deleteLater)
        self.addCleanup(window.close)
        sources, projects, montage = window.home_menus
        self.assertNotIn(window.new_project_action, sources.actions())
        self.assertIn(window.new_montage_action, montage.actions())
        self.assertIn(window.delete_project_action, projects.actions())
        self.assertNotIn(window.delete_project_action, window.main_toolbar.actions())
        self.assertEqual(0, window.layout().contentsMargins().left())
        self.assertEqual(0, window.main_toolbar.contentsMargins().left())

    def test_cancelling_file_selection_never_calls_the_removal_service(self):
        client = Mock()
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=('', '')):
            remove_project(None, client)
        client.remove_project_files.assert_not_called()

    def test_confirmation_defaults_to_no_and_json_only(self):
        client = Mock()
        client.remove_project_files.return_value = {'files': ['/Film.json'], 'token': 'token'}
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=('/Film.json', '')), \
                patch.object(QtWidgets.QDialog, 'exec', return_value=QtWidgets.QDialog.DialogCode.Accepted), \
                patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.No) as question:
            remove_project(None, client)
        client.remove_project_files.assert_called_once_with('/Film.json', dependencies=False)
        self.assertEqual(QtWidgets.QMessageBox.StandardButton.No, question.call_args.args[-1])
