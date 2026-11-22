import json
import shutil
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    if error.name != 'PySide6':
        raise
    raise unittest.SkipTest('PySide6 is unavailable') from error

from video_encoder_ui.quarantine_forecast import quarantine_forecast
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

    def test_forecast_projects_daily_disk_space_without_enrolling_or_purging(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scheduled = root / 'Film.m2t'
            scheduled.write_bytes(b'a' * 4096)
            (root / 'Ancien.m2t').write_bytes(b'b' * 1024)
            (root / 'Bloqué.m2t').write_bytes(b'c' * 2048)
            deadline = datetime(2026, 11, 30, 12).astimezone().isoformat()
            entries = [
                dict(entry('scheduled'), path=str(scheduled), delete_after=deadline),
                dict(entry('untracked'), path=str(root / 'Ancien.m2t')),
                dict(entry('blocked'), path=str(root / 'Bloqué.m2t'), delete_after=deadline),
            ]
            report = dict(response(entries), root=str(root))
            disk = shutil.disk_usage(root)._replace(total=100_000, free=50_000)
            with patch('video_encoder_ui.quarantine_forecast.shutil.disk_usage', return_value=disk):
                total, observed_disk, rows = quarantine_forecast(report, datetime(2026, 11, 30, 2))
            self.assertEqual(7168, total)
            self.assertEqual(disk, observed_disk)
            self.assertEqual([
                (date(2026, 11, 30), 0, 0, 7168, disk.free),
                (date(2026, 12, 1), 1, 4096, 3072, disk.free + scheduled.stat().st_blocks * 512),
            ], rows)

            dialog, client = self.dialog()
            client.request.return_value = report
            with patch.object(QtWidgets.QDialog, 'exec'), \
                    patch.object(QuarantinePolicyDialog, 'timer_status', return_value='Minuteur actif'):
                button = next(button for button in dialog.findChildren(QtWidgets.QPushButton)
                              if button.text() == 'Échéancier estimatif…')
                button.click()
            self.assertEqual([unittest.mock.call(), unittest.mock.call()], client.request.call_args_list)
            self.assertTrue(scheduled.exists())

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

    def test_filter_hides_only_missing_captures_and_can_show_them_again(self):
        dialog, client = self.dialog()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            missing = root / 'absent.m2t'
            present = root / 'capture.m2t'
            present.touch()
            link = root / 'lien.m2t'
            link.symlink_to(missing)
            entries = [dict(entry('blocked'), path=str(path)) for path in (missing, present, link)]
            client.request.return_value = dict(response(entries), root=str(root))
            with patch.object(QuarantinePolicyDialog, 'timer_status', return_value='Minuteur actif'):
                dialog.refresh()
                self.assertTrue(dialog.table.isRowHidden(0))
                self.assertFalse(dialog.table.isRowHidden(1))
                self.assertFalse(dialog.table.isRowHidden(2))
                self.assertIn('(1)', dialog.hide_absent.text())
                dialog.hide_absent.setChecked(False)
                self.assertFalse(dialog.table.isRowHidden(0))
                self.assertEqual('Absente', dialog.table.item(0, 3).text())
                self.assertEqual('Conservée', dialog.table.item(1, 3).text())

                dialog.hide_absent.setChecked(True)
                missing.touch()
                dialog.refresh()
                self.assertFalse(dialog.table.isRowHidden(0))
                self.assertIn('(0)', dialog.hide_absent.text())
        self.assertTrue(all(call.args == () for call in client.request.call_args_list))

    def test_title_and_state_filters_combine_and_copy_only_visible_source(self):
        dialog, client = self.dialog([
            dict(entry('scheduled'), path='/commun/Quarantaine/Film A.m2t'),
            dict(entry('due'), path='/commun/Quarantaine/Film B.m2t'),
            dict(entry('due'), path='/commun/Quarantaine/Autre.m2t'),
        ])
        dialog.source_search.setText('fILm')
        dialog.state_filter.setCurrentIndex(dialog.state_filter.findData('due'))
        self.assertEqual([True, False, True], [dialog.table.isRowHidden(row) for row in range(3)])
        dialog.table.selectRow(1)
        dialog.copy_button.click()
        self.assertEqual('Film B.m2t', self.app.clipboard().text())
        dialog.source_search.setText('Autre')
        self.assertFalse(dialog.copy_button.isEnabled())
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
