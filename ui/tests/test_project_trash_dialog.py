import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest("PySide6 is unavailable")

from video_encoder_ui.project_trash_dialog import ProjectTrashDialog
from video_encoder_ui.trim_export_queue_client import TrimExportQueueError


class ProjectTrashDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.entry = dict(directory='/videos/.video_encoder_trash/uuid', project='/videos/Film.json',
                          deleted_at='2026-10-30T12:00:00+01:00', bytes=1024,
                          files=['/videos/Film.json'], token='token')
        self.client = Mock()
        self.client.project_trash.return_value = dict(entries=[self.entry], errors=[])
        self.dialog = ProjectTrashDialog(None, self.client)

    def tearDown(self):
        self.dialog.close()
        self.dialog.deleteLater()

    def test_lists_groups_and_requires_selection(self):
        self.assertEqual(1, self.dialog.table.rowCount())
        self.assertFalse(self.dialog.restore_button.isEnabled())
        self.assertTrue(self.dialog.empty_button.isEnabled())
        self.dialog.table.selectRow(0)
        self.assertEqual([self.entry], self.dialog.selected_entries())
        self.assertTrue(self.dialog.restore_button.isEnabled())

    def test_cancelled_purge_calls_no_mutation_and_defaults_to_no(self):
        self.client.reset_mock()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.No) as ask:
            self.dialog.apply('purge', [self.entry])
        self.client.project_trash.assert_not_called()
        self.assertEqual(QtWidgets.QMessageBox.StandardButton.No, ask.call_args.args[-1])

    def test_confirmed_restore_uses_the_exact_preview_token(self):
        self.client.reset_mock()
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Yes):
            self.dialog.apply('restore', [self.entry])
        self.client.project_trash.assert_any_call('restore', self.entry['directory'], 'token')

    def test_unknown_or_unavailable_contents_disable_emptying(self):
        self.client.project_trash.return_value = dict(entries=[self.entry], errors=['Volume indisponible'])
        self.dialog.refresh()
        self.assertFalse(self.dialog.empty_button.isEnabled())
        self.assertIn('indisponible', self.dialog.warning.text())

    def test_partial_batch_failure_is_reported(self):
        self.client.project_trash.side_effect = [TrimExportQueueError('Fichier changé'),
                                                dict(entries=[self.entry], errors=[])]
        with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Yes), \
                patch.object(QtWidgets.QMessageBox, 'warning') as warning:
            self.dialog.apply('purge', [self.entry])
        warning.assert_called_once()
        self.assertIn('Fichier changé', warning.call_args.args[-1])
