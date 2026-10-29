import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    if error.name != 'PySide6':
        raise
    raise unittest.SkipTest('PySide6 is unavailable') from error

from video_encoder_ui.trim_export_queue_dialog import TrimExportQueueDialog


class QueueSearchTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def job(self, number, name, status='done'):
        return {'id': str(number), 'kind': 'trim_export', 'input_path': f'/projets/{name}.json',
                'output_path': f'/videos/{name}.mkv', 'status': status, 'attempts': 1,
                'created_at': f'2026-10-29T10:{number:02d}:00+01:00'}

    def dialog(self, jobs, source_names=None):
        dialog = TrimExportQueueDialog(jobs, source_names=source_names or Mock(return_value='capture.m2t'))
        self.addCleanup(dialog.deleteLater)
        return dialog

    def test_search_is_available_immediately_and_can_be_cleared(self):
        dialog = self.dialog([self.job(1, 'Joséphine'), self.job(2, 'Haute saison')])
        self.assertFalse(dialog.search_widget.isHidden())
        self.assertTrue(dialog.search_field.isClearButtonEnabled())
        dialog.search_field.setText('JOSEPHINE')
        self.assertEqual(['1'], [job['id'] for job in dialog.displayed_jobs])
        self.assertEqual('1 tâche affichée sur 2', dialog.search_count.text())
        dialog.search_field.clear()
        self.assertEqual(2, dialog.jobs_table.rowCount())

    def test_source_and_status_words_can_be_combined(self):
        jobs = [self.job(1, 'A', 'failed'), self.job(2, 'B')]
        dialog = self.dialog(jobs, source_names=lambda path: 'Été.m2t' if 'A.json' in path else 'Hiver.m2t')
        dialog.search_field.setText('ete ECHEC')
        self.assertEqual(['1'], [job['id'] for job in dialog.displayed_jobs])

    def test_search_finds_a_job_older_than_the_recent_limit(self):
        dialog = self.dialog([self.job(number, f'Film-{number:02d}') for number in range(20)])
        self.assertEqual(15, dialog.jobs_table.rowCount())
        dialog.search_field.setText('Film-00')
        self.assertEqual(['0'], [job['id'] for job in dialog.displayed_jobs])
        dialog.search_field.clear()
        self.assertEqual(15, dialog.jobs_table.rowCount())

    def test_all_three_path_columns_are_searchable(self):
        job = self.job(1, 'film')
        dialog = self.dialog([job], source_names=Mock(return_value='source spéciale.m2t'))
        for query in ('/projets/film', '/videos/film', 'source speciale'):
            dialog.search_field.setText(query)
            self.assertEqual([job], dialog.displayed_jobs)

    def test_full_source_directory_is_indexed_from_the_project(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / 'Film.json'
            project.write_text(json.dumps({'format': 'video_encoder.trim_project', 'version': 2,
                'sources': [{'id': 'source', 'path': '/captures/Été/source.m2t', 'fps': 25, 'length': 100}],
                'timeline': []}), encoding='utf-8')
            job = self.job(1, 'film')
            job['input_path'] = str(project)
            dialog = TrimExportQueueDialog([job])
            self.addCleanup(dialog.deleteLater)
            dialog.search_field.setText('/captures/ete')
            self.assertEqual([job], dialog.displayed_jobs)

    def test_typing_does_not_read_source_names_again(self):
        names = Mock(return_value='source.m2t')
        dialog = self.dialog([self.job(1, 'film')], names)
        initial = names.call_count
        for query in ('s', 'so', 'sou', 'source', ''):
            dialog.search_field.setText(query)
        self.assertEqual(initial, names.call_count)

    def test_a_visible_selection_survives_search_and_refresh(self):
        job = self.job(1, 'Film', 'failed')
        dialog = self.dialog([job, self.job(2, 'Autre')])
        dialog.jobs_table.selectRow(1)
        dialog.search_field.setText('film')
        self.assertEqual('1', dialog.selected_job()['id'])
        dialog.set_jobs([{**job, 'attempts': 2}])
        self.assertEqual('1', dialog.selected_job()['id'])
        self.assertEqual('film', dialog.search_field.text())

    def test_hidden_selection_is_cleared_and_cannot_trigger_an_action(self):
        dialog = self.dialog([self.job(1, 'Film', 'queued'), self.job(2, 'Autre', 'queued')])
        dialog.jobs_table.selectRow(1)
        signal = Mock()
        dialog.start_selected_requested.connect(signal)
        dialog.search_field.setText('autre')
        self.assertIsNone(dialog.selected_job())
        self.assertFalse(dialog.start_selected_button.isEnabled())
        dialog.request_selected_start()
        signal.assert_not_called()

    def test_filter_does_not_change_the_scope_of_launching_the_queue(self):
        dialog = self.dialog([self.job(1, 'Film', 'queued')])
        signal = Mock()
        dialog.start_requested.connect(signal)
        dialog.search_field.setText('no match')
        self.assertEqual(0, dialog.jobs_table.rowCount())
        self.assertTrue(dialog.start_button.isEnabled())
        dialog.start_button.click()
        signal.assert_called_once_with()

    def test_progress_survives_filtering_and_reappears_when_the_filter_is_cleared(self):
        job = self.job(1, 'Film', 'running')
        dialog = self.dialog([job])
        dialog.set_progress({'stage': 'video', 'step': 1, 'total': 3})
        dialog.set_percentage(42)
        dialog.search_field.setText('no match')
        dialog.search_field.clear()
        self.assertIn('42', dialog.jobs_table.item(0, 3).text())
        self.assertIn('Vidéo', dialog.jobs_table.item(0, 3).text())
