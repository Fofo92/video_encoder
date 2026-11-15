import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from PySide6 import QtCore, QtWidgets
except ImportError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui import dvd_import_dialog as ui


@unittest.skipIf(QtWidgets is None, 'PySide6 unavailable')
class DvdImportDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_preparation_dialog_starts_with_no_assumed_title_mapping(self):
        dialog = ui.DvdImportDialog(None, Mock())
        self.assertEqual('/dev/sr0', dialog.device.text())
        self.assertEqual(0, dialog.titles.count())
        self.assertFalse(dialog.episodic.isChecked())
        dialog.deleteLater()

    def test_menu_fills_the_first_identified_title_without_a_second_picker(self):
        dialog = ui.DvdImportDialog(None, Mock())
        self.addCleanup(dialog.deleteLater)
        for number in (1, 2, 3):
            dialog.titles.addItem(f'Titre {number}', {'title': number, 'device': '/dev/sr0'})
        result = {'series_title': 'Code Quantum', 'episodes': [
            {'dvd_title': 2, 'season': 2, 'episode': 16, 'record_id': 42,
             'french_title': 'Aux portes de la mort', 'original_title': ''},
            {'dvd_title': 3, 'season': 2, 'episode': 17, 'record_id': 43,
             'french_title': 'Au revoir mon ange', 'original_title': ''},
        ]}
        dialog.show_menu_episodes(result)
        self.assertEqual(1, dialog.titles.currentIndex())
        self.assertEqual('Code Quantum', dialog.title.text())
        self.assertEqual((2, 16, 42), (dialog.season.value(), dialog.episode.value(), dialog.selected_menu_record_id()))
        self.assertIn('Au revoir mon ange', dialog.titles.itemText(2))

        dialog.titles.setCurrentIndex(0)
        dialog.use_menu_episode(0)
        self.assertIsNone(dialog.selected_menu_record_id())

    def test_resuming_a_copy_uses_the_stored_episode_even_with_another_title_selected(self):
        dialog = ui.DvdImportDialog(None, Mock())
        self.addCleanup(dialog.deleteLater)
        dialog.title.setText('Autre série')
        copied = {'path': '/commun/to_be_cut/DVD/title.mkv', 'menu_episode': {
            'series': 'Code Quantum', 'season': 2, 'episode': 16, 'record_id': 42}}
        with tempfile.TemporaryDirectory() as directory:
            sidecar = Path(directory) / 'dvd-source.json'
            sidecar.write_text(json.dumps(copied))
            with patch.object(ui.QtWidgets.QFileDialog, 'getOpenFileName', return_value=(str(sidecar), '')), \
                    patch.object(ui, 'choose_tracks', return_value=([], [])), \
                    patch.object(ui, 'new_project', return_value={}), \
                    patch.object(ui, 'identify_destination', return_value=None) as identify:
                dialog.resume()
        self.assertEqual(42, identify.call_args.kwargs['record_id'])
        self.assertIn('S02 E16', identify.call_args.args[2].name)
        dialog.client.enqueue.assert_not_called()

    def test_cancelled_track_selection_does_not_prepare_a_job(self):
        dialog = ui.DvdImportDialog(None, Mock())
        with patch.object(ui, 'choose_tracks', return_value=None), \
                patch.object(ui.QtWidgets.QMessageBox, 'information'), \
                patch.object(ui, 'identify_destination') as identify:
            dialog.finish_copy({'path': '/commun/to_be_cut/DVD/title.mkv'})
        identify.assert_not_called()
        dialog.client.enqueue.assert_not_called()
        dialog.deleteLater()

    def test_vidb_metadata_drives_episode_name_including_both_original_titles(self):
        document = {'project_id': 'project', 'sources': []}
        result = {'status': 'identified', 'record_id': 42, 'metadata': {
            'record_kind': 'episode', 'french_title': 'Un phalangiste de province',
            'original_title': 'Un falangista de provincias', 'season_number': 1, 'episode_number': 1,
            'series_french_title': "Anatomie d'un instant", 'series_original_title': 'Anatomía de un instante',
            'series_year': 2025, 'series_titles': [], 'countries': ['Espagne', 'France']}}
        with patch('video_encoder_ui.vidb_project_link.VidbProjectLink.identify', return_value=result):
            output = ui.identify_destination(None, document, Path('/videos/provisional.mkv'))
        self.assertEqual("S01 E01 - Un phalangiste de province (Un falangista de provincias).mkv", output.name)
        self.assertEqual("Anatomie d'un instant (Anatomía de un instante) (2025)", output.parent.parent.name)
        self.assertEqual(result, document['vidb'])

    def test_project_is_saved_before_queueing_and_retained_after_queue_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'Été.mkv'
            document = {'vidb': {'record_id': 42}}
            client = Mock()
            client.enqueue.side_effect = ui.TrimExportQueueError('queue unavailable')
            with patch.object(QtWidgets.QMessageBox, 'question', return_value=QtWidgets.QMessageBox.StandardButton.Yes):
                with self.assertRaisesRegex(ValueError, 'Projet conservé'):
                    ui.save_and_enqueue(None, document, output, client)
            self.assertEqual(document, json.loads(output.with_suffix('.json').read_text()))
            client.enqueue.assert_called_once_with(output.with_suffix('.json'), output)

    def test_resume_does_not_enqueue_a_project_already_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'dvd.json'
            path.write_text('{}')
            client = Mock()
            client.list_jobs.return_value = [{'input_path': str(path), 'status': 'queued'}]
            with patch.object(QtWidgets.QMessageBox, 'information'):
                ui.reopen_dvd_project(None, path, client)
            client.enqueue.assert_not_called()

    def test_copy_helper_cancellation_terminates_the_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'slow.py'
            script.write_text('import time; time.sleep(20)')

            def click_cancel():
                for widget in self.app.allWidgets():
                    if isinstance(widget, QtWidgets.QProgressDialog):
                        buttons = widget.findChildren(QtWidgets.QPushButton)
                        if buttons:
                            buttons[0].click()

            QtCore.QTimer.singleShot(100, click_cancel)
            with patch.object(ui, 'PIPELINE', script):
                with self.assertRaisesRegex(ValueError, 'annulée'):
                    ui.helper(None, 'Copying')

    def test_helper_drains_output_without_blocking_and_reports_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'helper.py'
            script.write_text('print(\'{"titles": [2]}\')')
            with patch.object(ui, 'PIPELINE', script):
                self.assertEqual({'titles': [2]}, ui.helper(None, 'Testing'))
            script.write_text('import sys; print("copy failed", file=sys.stderr); sys.exit(1)')
            with patch.object(ui, 'PIPELINE', script):
                with self.assertRaisesRegex(ValueError, 'copy failed'):
                    ui.helper(None, 'Testing')


if __name__ == '__main__':
    unittest.main()
