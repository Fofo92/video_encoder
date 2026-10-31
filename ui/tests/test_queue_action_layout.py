import unittest
from unittest.mock import patch

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
            self.assertEqual('File d’attente', dialog.queue_actions_title.text())
            self.assertEqual('Tâche', dialog.task_actions_title.text())
            self.assertNotIsInstance(dialog.queue_actions_group, QtWidgets.QGroupBox)
            self.assertNotIsInstance(dialog.task_actions_group, QtWidgets.QGroupBox)
            self.assertIsInstance(dialog.queue_actions_group, QtWidgets.QFrame)
            self.assertEqual(QtWidgets.QFrame.Shape.StyledPanel, dialog.queue_actions_group.frameShape())
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
            self.assertIsInstance(group.layout(), QtWidgets.QHBoxLayout)
            self.assertIsInstance(group.layout().itemAt(0).widget(), QtWidgets.QLabel)
            self.assertIs(toolbars[0], group.layout().itemAt(1).widget())
            self.assertEqual(dialog.jobs_table.verticalHeader().defaultSectionSize(), group.height())
        self.assertEqual(3, len(dialog.findChildren(QtWidgets.QToolBar)))
        self.assertIs(dialog.main_toolbar.parentWidget(), dialog)
        self.assertNotIn(dialog.main_toolbar, dialog.queue_actions_group.findChildren(QtWidgets.QToolBar))
        self.assertNotIn(dialog.main_toolbar, dialog.task_actions_group.findChildren(QtWidgets.QToolBar))

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
        self.assertEqual('Lancer', dialog.start_button.property('home_action').text())
        dialog.set_finish_current_requested(True)
        self.assertEqual(dialog.finish_current_button.text(), dialog.finish_current_button.property('home_action').text())
        dialog.set_running(False)

    def test_refresh_time_is_in_the_title_without_taking_a_layout_row(self):
        dialog = self.dialog(StartWindow)
        dialog.mark_refreshed('09:42:17')
        self.assertEqual('video_encoder — Montages — dernière actualisation : 09:42:17', dialog.windowTitle())
        self.assertTrue(dialog.refresh_status_label.isHidden())
        self.assertEqual(-1, dialog.layout().indexOf(dialog.refresh_status_label))
        self.assertEqual(0, dialog.layout().indexOf(dialog.main_toolbar))
        self.assertEqual(1, dialog.layout().indexOf(dialog.queue_actions_group))
        self.assertEqual(2, dialog.layout().indexOf(dialog.task_actions_group))

    def test_task_bar_is_only_shown_for_a_visible_selection(self):
        dialog = self.dialog(StartWindow)
        self.assertTrue(dialog.task_actions_group.isHidden())
        dialog.set_jobs([{'id': 'one', 'input_path': 'film.json', 'status': 'queued'}])
        self.assertTrue(dialog.task_actions_group.isHidden())
        dialog.jobs_table.selectRow(0)
        self.assertFalse(dialog.task_actions_group.isHidden())
        dialog.search_field.setText('no match')
        self.assertTrue(dialog.task_actions_group.isHidden())
        self.assertFalse(dialog.queue_actions_group.isHidden())

    def test_toolbar_labels_are_short_and_keep_the_two_explicit_exceptions(self):
        dialog = self.dialog(StartWindow)
        for name, label in (('start_button', 'Lancer'), ('start_selected_button', 'Lancer'),
                            ('retry_button', 'Relancer'), ('stop_button', 'Interrompre'),
                            ('remove_button', 'Supprimer'), ('output_button', 'Modifier…'),
                            ('delete_project_button', 'Supprimer tâche et JSON…'),
                            ('finish_current_button', 'Arrêter après le montage en cours')):
            self.assertEqual(label, getattr(dialog, name).property('home_action').text())

    def test_exit_is_at_the_right_of_the_menu_and_not_in_the_footer(self):
        dialog = self.dialog(StartWindow)
        self.assertIs(dialog.exit_menu_bar, dialog.menu_bar.cornerWidget(QtCore.Qt.Corner.TopRightCorner))
        self.assertEqual('Quitter', dialog.exit_action.text())
        for box in dialog.findChildren(QtWidgets.QDialogButtonBox):
            if box.button(QtWidgets.QDialogButtonBox.StandardButton.Close) is not None:
                self.assertTrue(box.isHidden())
        dialog.exit_action.trigger()
        self.assertEqual(QtWidgets.QDialog.DialogCode.Rejected, dialog.result())

    def test_exit_menu_keeps_the_running_encoding_guard(self):
        dialog = self.dialog(StartWindow)
        dialog.set_running(True)
        with patch.object(QtWidgets.QMessageBox, 'information') as warning:
            dialog.exit_action.trigger()
        warning.assert_called_once()
        dialog.set_running(False)

    def test_status_counts_all_pending_jobs_even_when_the_search_hides_them(self):
        dialog = self.dialog(StartWindow)
        dialog.set_jobs([{'id': str(index), 'input_path': f'film{index}.json', 'status': state}
                         for index, state in enumerate(('queued', 'queued', 'deferred', 'done', 'running'))])
        self.assertEqual('Encodage en cours — 2 tâches en attente', dialog.status_bar.currentMessage())
        dialog.search_field.setText('no match')
        self.assertEqual(0, dialog.jobs_table.rowCount())
        self.assertEqual('Encodage en cours — 2 tâches en attente', dialog.status_bar.currentMessage())

    def test_status_updates_when_the_runner_starts_and_stops_and_jobs_refresh(self):
        dialog = self.dialog(StartWindow)
        self.assertEqual('Aucun encodage en cours — 0 tâches en attente', dialog.status_bar.currentMessage())
        dialog.set_jobs([{'id': 'one', 'input_path': 'film.json', 'status': 'queued'}])
        self.assertEqual('Aucun encodage en cours — 1 tâche en attente', dialog.status_bar.currentMessage())
        dialog.set_running(True)
        self.assertEqual('Encodage en cours — 1 tâche en attente', dialog.status_bar.currentMessage())
        dialog.set_jobs([{'id': 'one', 'input_path': 'film.json', 'status': 'done'}])
        dialog.set_running(False)
        self.assertEqual('Aucun encodage en cours — 0 tâches en attente', dialog.status_bar.currentMessage())
        self.assertIs(dialog.status_bar, dialog.layout().itemAt(dialog.layout().count() - 1).widget())
