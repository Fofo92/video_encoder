import json
import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    if error.name != 'PySide6':
        raise
    raise unittest.SkipTest('PySide6 is unavailable') from error

from video_encoder_ui.quarantine_policy_dialog import QuarantinePolicyClient, QuarantinePolicyDialog
from video_encoder_ui.trim_export_queue_client import TrimExportQueueError
from video_encoder_ui.start_window import StartWindow


def response(entries=None):
    return {'format': 'video_encoder.quarantine', 'version': 1, 'entries': entries or [], 'errors': [], 'deleted': []}


def entry(state='untracked'):
    return {'path': '/commun/Quarantaine/Film.m2t', 'state': state, 'entered_at': None,
            'delete_after': '2026-11-30T12:00:00Z' if state != 'untracked' else None,
            'reason': 'Vérification nécessaire', 'projects': []}


class QuarantinePolicyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def dialog(self, entries=None):
        client = Mock()
        client.request.return_value = response(entries)
        with patch.object(QuarantinePolicyDialog, 'timer_status', return_value='Minuteur inactif'):
            dialog = QuarantinePolicyDialog(client=client)
        self.addCleanup(dialog.deleteLater)
        return dialog, client

    def test_client_uses_the_quarantine_command_and_validates_its_response(self):
        queue = Mock()
        queue.manage.return_value = json.dumps(response())
        self.assertEqual([], QuarantinePolicyClient(queue).request()['entries'])
        queue.manage.assert_called_once_with('quarantine', 'list')
        for invalid in ('invalid JSON', '[]', '{}'):
            queue.manage.return_value = invalid
            with self.assertRaises(TrimExportQueueError):
                QuarantinePolicyClient(queue).request()

    def test_opening_the_view_only_lists_and_never_deletes_or_enrolls(self):
        dialog, client = self.dialog([entry('due')])
        client.request.assert_called_once_with()
        self.assertEqual('Échue', dialog.table.item(0, 3).text())
        self.assertFalse(dialog.enroll_button.isEnabled())

    def test_preview_is_read_only_and_reports_due_files(self):
        dialog, client = self.dialog([entry('due')])
        with patch.object(QuarantinePolicyDialog, 'timer_status', return_value='Minuteur actif'), \
                patch.object(QtWidgets.QMessageBox, 'information') as message:
            dialog.preview()
        self.assertIn('/commun/Quarantaine/Film.m2t', message.call_args.args[2])
        self.assertTrue(all(call.args == () for call in client.request.call_args_list))

    def test_legacy_enrollment_is_enabled_only_for_an_untracked_selection(self):
        dialog, client = self.dialog([entry()])
        dialog.table.selectRow(0)
        self.assertTrue(dialog.enroll_button.isEnabled())
        with patch.object(QuarantinePolicyDialog, 'timer_status', return_value='Minuteur actif'):
            dialog.enroll()
        self.assertIn(unittest.mock.call('enroll', '/commun/Quarantaine/Film.m2t'), client.request.call_args_list)
        self.assertNotIn(unittest.mock.call('sweep', '--apply'), client.request.call_args_list)

    def test_a_blocked_entry_shows_its_reason_and_cannot_be_forced(self):
        dialog, client = self.dialog([entry('blocked')])
        dialog.table.selectRow(0)
        self.assertFalse(dialog.enroll_button.isEnabled())
        self.assertFalse(dialog.associate_button.isEnabled())
        self.assertEqual('Vérification nécessaire', dialog.table.item(0, 4).text())
        dialog.enroll()
        client.request.assert_called_once_with()

    def test_explicit_project_association_does_not_request_a_deletion(self):
        dialog, client = self.dialog([entry()])
        dialog.table.selectRow(0)
        with patch.object(QtWidgets.QFileDialog, 'getOpenFileName', return_value=('/videos/Film.json', '')), \
                patch.object(QuarantinePolicyDialog, 'timer_status', return_value='Minuteur actif'):
            dialog.associate_project()
        self.assertIn(unittest.mock.call('enroll', '/commun/Quarantaine/Film.m2t', '--project', '/videos/Film.json'),
                      client.request.call_args_list)

    def test_timer_status_distinguishes_active_from_inactive(self):
        for status, label in [('active\n', 'minuteur actif'), ('inactive\n', 'minuteur inactif')]:
            with patch('video_encoder_ui.quarantine_policy_dialog.subprocess.run', return_value=Mock(stdout=status)):
                self.assertIn(label, QuarantinePolicyDialog.timer_status())

    def test_home_sources_menu_exposes_the_view_without_changing_toolbars(self):
        window = StartWindow()
        self.addCleanup(window.deleteLater)
        self.assertIn(window.quarantine_policy_action, window.home_menus[0].actions())
        self.assertIs(window.quarantine_policy_action.parent(), window)
        sources = window.home_menus[0]
        actions = sources.actions()
        sources.clear()
        for action in actions:
            sources.addAction(action)
        self.assertEqual('Suivi de la quarantaine…', window.quarantine_policy_action.text())
        self.assertNotIn(window.quarantine_policy_action, window.main_toolbar.actions())
        with patch('video_encoder_ui.quarantine_policy_dialog.show_quarantine_policy') as show:
            window.quarantine_policy_action.trigger()
        show.assert_called_once_with(window)
