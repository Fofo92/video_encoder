import unittest

try:
    from PySide6 import QtCore, QtWidgets
except ModuleNotFoundError as error:
    if error.name != 'PySide6':
        raise
    raise unittest.SkipTest('PySide6 is unavailable') from error

from video_encoder_ui.start_window import StartWindow
from video_encoder_ui.trim_export_queue_dialog import TrimExportQueueDialog


class QueueActionLayoutTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def dialog(self, kind=TrimExportQueueDialog):
        dialog = kind([]) if kind is TrimExportQueueDialog else kind()
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_action_groups_are_named_and_above_the_table_in_both_windows(self):
        for kind in (TrimExportQueueDialog, StartWindow):
            dialog = self.dialog(kind)
            self.assertIn('File d’attente', dialog.queue_actions_group.title())
            self.assertEqual('Tâche sélectionnée', dialog.task_actions_group.title())
            self.assertLess(dialog.layout().indexOf(dialog.queue_actions_group), dialog.layout().indexOf(dialog.jobs_table))
            self.assertLess(dialog.layout().indexOf(dialog.task_actions_group), dialog.layout().indexOf(dialog.jobs_table))
            self.assertIs(dialog.start_button.parent(), dialog.queue_buttons)
            self.assertIs(dialog.start_selected_button.parent(), dialog.job_buttons)

    def test_home_toolbars_stay_in_their_groups_and_show_text(self):
        dialog = self.dialog(StartWindow)
        for group in (dialog.queue_actions_group, dialog.task_actions_group):
            toolbars = group.findChildren(QtWidgets.QToolBar)
            self.assertEqual(1, len(toolbars))
            self.assertEqual(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon, toolbars[0].toolButtonStyle())
            self.assertTrue(all(action.text() for action in toolbars[0].actions()))
        self.assertEqual(2, len(dialog.findChildren(QtWidgets.QToolBar)))

    def test_error_panel_only_appears_for_failed_or_interrupted_tasks_with_details(self):
        dialog = self.dialog()
        self.assertTrue(dialog.error_group.isHidden())
        for status, message, visible in (('queued', '', False), ('running', 'old error', False),
                                         ('done', 'old error', False), ('failed', '', False),
                                         ('failed', 'ffmpeg error', True), ('interrupted', 'stopped', True)):
            dialog.set_jobs([{'id': 'one', 'input_path': 'film.json', 'status': status, 'error': message}])
            dialog.jobs_table.selectRow(0)
            self.assertEqual(not visible, dialog.error_group.isHidden(), status)
            if visible:
                self.assertEqual(message, dialog.error_details.toPlainText())

    def test_resolved_error_disappears_on_refresh_even_if_the_old_message_is_retained(self):
        dialog = self.dialog()
        job = {'id': 'one', 'input_path': 'film.json', 'status': 'failed', 'error': 'error'}
        dialog.set_jobs([job])
        dialog.jobs_table.selectRow(0)
        self.assertFalse(dialog.error_group.isHidden())
        dialog.set_jobs([{**job, 'status': 'done'}])
        self.assertTrue(dialog.error_group.isHidden())
        self.assertEqual('', dialog.error_details.toPlainText())

    def test_filtering_out_the_failed_selection_hides_the_error_panel(self):
        dialog = self.dialog()
        dialog.set_jobs([{'id': 'one', 'input_path': 'film.json', 'status': 'failed', 'error': 'error'}])
        dialog.jobs_table.selectRow(0)
        dialog.search_field.setText('no match')
        self.assertTrue(dialog.error_group.isHidden())
        self.assertIsNone(dialog.selected_job())

    def test_home_action_text_tracks_dynamic_button_labels(self):
        dialog = self.dialog(StartWindow)
        dialog.set_jobs([{'id': 'one', 'input_path': 'film.json', 'status': 'deferred'}])
        dialog.jobs_table.selectRow(0)
        self.assertEqual(dialog.defer_button.text(), dialog.defer_button.property('home_action').text())
        dialog.set_running(True)
        self.assertEqual(dialog.start_button.text(), dialog.start_button.property('home_action').text())
        dialog.set_finish_current_requested(True)
        self.assertEqual(dialog.finish_current_button.text(), dialog.finish_current_button.property('home_action').text())
        dialog.set_running(False)
