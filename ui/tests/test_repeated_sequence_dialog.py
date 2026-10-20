import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

try:
    from PySide6 import QtCore, QtGui, QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets:
    from video_encoder_ui.repeated_sequence_dialog import RepeatedSequenceDialog
    from video_encoder_ui.repeated_sequence_review import identity


@unittest.skipIf(QtWidgets is None, 'PySide6 unavailable')
class RepeatedSequenceDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.m2t'
        self.source.write_bytes(b'source')
        image = QtGui.QImage(32, 18, QtGui.QImage.Format.Format_RGB32)
        image.fill(QtCore.Qt.GlobalColor.blue)
        frame_source = SimpleNamespace(length=2000, frame_at=lambda position: (image, position, 1))
        self.dialog = RepeatedSequenceDialog(self.source, (10, 1900), frame_source)
        self.dialog.expert.setChecked(True)
        self.addCleanup(self.dialog.reject)
        self.report = {'status': 'experimental', 'source': str(self.source), 'sample_fps': 5,
                       'source_identity': identity(self.source), 'index_limits_reached': True,
                       'candidates': [{'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 3}
                                                      for value in [5, 20, 40, 60]]}]}
        self.path = Path(self.temp.name) / 'resultat.json'
        self.path.write_text(json.dumps(self.report))

    def test_report_shows_limits_and_requires_group_selection(self):
        self.dialog.load_report(self.path)
        self.assertEqual(self.dialog.groups.rowCount(), 1)
        self.assertIn('plafonds', self.dialog.notice.text())
        self.assertFalse(self.dialog.refine_button.isEnabled())
        self.assertFalse(self.dialog.apply_button.isEnabled())
        self.dialog.groups.selectRow(0)
        self.assertTrue(self.dialog.refine_button.isEnabled())
        self.assertEqual(self.dialog.hits.count(), 4)
        self.assertFalse(self.dialog.confirm.isEnabled())
        self.assertFalse(self.dialog.preview.pixmap().isNull())

    def test_refinement_passes_explicit_group_and_only_outer_bounds(self):
        self.dialog.load_report(self.path)
        self.dialog.groups.selectRow(0)
        with patch.object(self.dialog, 'start') as start:
            self.dialog.refine_group()
        args = start.call_args.args[2]
        self.assertEqual(args[args.index('--candidate') + 1], '1')
        self.assertEqual(args[args.index('--start-frame') + 1], '10')
        self.assertNotIn('--reference', args)

    def test_rejects_report_from_changed_source(self):
        self.source.write_bytes(b'changed')
        with patch('video_encoder_ui.repeated_sequence_dialog.QtWidgets.QMessageBox.warning') as warning:
            self.dialog.load_report(self.path)
        warning.assert_called_once()
        self.assertEqual(self.dialog.groups.rowCount(), 0)

    def test_refinement_requires_explicit_confirmation_before_replacing_montage(self):
        self.dialog.load_report(self.path)
        self.dialog.groups.selectRow(0)
        refined = {'status': 'experimental', 'source': str(self.source), 'source_identity': identity(self.source),
                   'outer_bounds': [10, 1900], 'refinement': {'status': 'experimental'},
                   'coordinate_basis': 'FFmpeg decoded source frame index; editor mapping unverified',
                   'source_motif_limits': [{'motif_start_decoded_frame': start, 'motif_end_decoded_frame_exclusive': start + 75}
                                          for start in [125, 500, 1000, 1500]]}
        output = Path(self.temp.name) / 'refined'
        output.mkdir()
        (output / 'manifest.json').write_text(json.dumps(refined))
        self.dialog.output, self.dialog.task, self.dialog.busy = output, 'refinement', True
        self.dialog.process_finished(0, QtCore.QProcess.ExitStatus.NormalExit)
        self.assertFalse(self.dialog.apply_button.isEnabled())
        self.dialog.confirm.setChecked(True)
        self.assertTrue(self.dialog.apply_button.isEnabled())
        self.dialog.apply_segments()
        self.assertEqual(len(self.dialog.session.segments), 3)
        self.assertEqual(self.dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)

    def test_cancel_stops_a_real_background_process_without_accepting_segments(self):
        import time
        root = Path(self.temp.name)
        scripts = root / 'script' / 'research'
        scripts.mkdir(parents=True)
        (scripts / 'sleep.py').write_text('import time\ntime.sleep(60)\n')
        self.dialog.repository = root
        self.dialog.start('discovery', 'sleep.py', [], root / 'output')
        self.assertTrue(self.dialog.process.waitForStarted(2000))
        self.assertTrue(self.dialog.busy)
        self.assertFalse(self.dialog.open_button.isEnabled())
        before = time.monotonic()
        self.dialog.reject()
        self.app.processEvents()
        self.assertLess(time.monotonic() - before, 4)
        self.assertEqual(self.dialog.process.state(), QtCore.QProcess.ProcessState.NotRunning)
        self.assertIsNone(self.dialog.session)
        self.assertFalse(self.dialog.busy)

    def test_group_above_limit_cannot_launch_refinement(self):
        self.report['candidates'][0]['occurrences'] = [
            {'core_start_seconds': value, 'core_end_seconds': value + 2} for value in range(1, 61, 4)]
        self.path.write_text(json.dumps(self.report))
        self.dialog.load_report(self.path)
        self.assertEqual(self.dialog.groups.rowCount(), 0)
        self.dialog.advanced.setChecked(True)
        self.dialog.groups.selectRow(0)
        self.assertFalse(self.dialog.refine_button.isEnabled())
        self.assertIn('15 occurrences', self.dialog.notice.text())
        with patch.object(self.dialog, 'start') as start:
            self.dialog.refine_group()
        start.assert_not_called()

    def test_long_traceback_does_not_expand_window_or_error_popup(self):
        trace = 'Traceback\\n' + '/long/path/' * 1000 + '\nValueError: invalid group'
        with patch('video_encoder_ui.repeated_sequence_dialog.QtWidgets.QMessageBox.warning') as warning:
            self.dialog.error(trace)
        self.assertEqual(warning.call_args.args[2], 'ValueError: invalid group')
        self.assertEqual(self.dialog.notice.text(), 'ValueError: invalid group')
        self.dialog.show()
        self.app.processEvents()
        self.assertLessEqual(self.dialog.width(), 1000)

    def test_automatic_mode_hides_groups_and_launches_common_family_without_selection(self):
        self.dialog.expert.setChecked(False)
        self.dialog.bounds = (0, 20000)
        self.report['candidates'] = [{'occurrences': [
            {'core_start_seconds': t, 'core_end_seconds': t + 2} for t in [100, 200, 300, 400]]}]
        self.path.write_text(json.dumps(self.report))
        self.dialog.load_report(self.path)
        self.assertTrue(self.dialog.groups.isHidden())
        self.assertTrue(self.dialog.paired.isHidden())
        self.assertTrue(self.dialog.refine_button.isEnabled())
        self.assertEqual(self.dialog.groups.currentRow(), -1)
        with patch.object(self.dialog, 'start') as start:
            self.dialog.refine_group()
        self.assertIn('--candidate', start.call_args.args[2])
        self.assertIn('2 plage', self.dialog.stage.text())
        self.assertFalse(self.dialog.confirm.isChecked())
        self.assertFalse(self.dialog.apply_button.isEnabled())

    def test_graphical_fallback_is_labelled_and_never_auto_confirmed(self):
        refined = {'status': 'experimental', 'source': str(self.source), 'source_identity': identity(self.source),
                   'outer_bounds': list(self.dialog.bounds),
                   'refinement': {'status': 'experimental', 'graphic_fallback_used': True},
                   'coordinate_basis': 'FFmpeg decoded source frame index; editor mapping unverified',
                   'source_motif_limits': [{'motif_start_decoded_frame': start,
                                           'motif_end_decoded_frame_exclusive': start + 75}
                                          for start in [125, 500, 1000, 1500]]}
        self.dialog.display_refinement(refined)
        self.assertIn('graphiques expérimentaux', self.dialog.notice.text())
        self.assertFalse(self.dialog.confirm.isChecked())
        self.assertFalse(self.dialog.apply_button.isEnabled())

    def test_automatic_failure_does_not_claim_no_advertisements(self):
        self.dialog.expert.setChecked(False)
        self.report['candidates'] = []
        self.path.write_text(json.dumps(self.report))
        self.dialog.load_report(self.path)
        self.assertFalse(self.dialog.refine_button.isEnabled())
        self.assertIn('ne prouve pas', self.dialog.stage.text())

    def test_error_keeps_output_folder_available_for_copy_without_long_label(self):
        self.dialog.output = Path(self.temp.name) / 'failed-refinement'
        with patch('video_encoder_ui.repeated_sequence_dialog.QtWidgets.QMessageBox.warning'):
            self.dialog.error('Traceback\nValueError: ambiguous motif')
        self.assertFalse(self.dialog.copy_diagnostic.isHidden())
        self.dialog.copy_diagnostic.click()
        self.assertEqual(self.app.clipboard().text(), str(self.dialog.output.resolve()))
        self.assertEqual(self.dialog.notice.text(), 'ValueError: ambiguous motif')

    def test_approximate_preview_cannot_be_reviewed_while_refinement_runs(self):
        self.dialog.load_report(self.path)
        self.dialog.groups.selectRow(0)
        with patch.object(self.dialog.process, 'start'):
            self.dialog.refine_group()
        self.assertTrue(self.dialog.busy)
        self.assertIn('Calcul en cours', self.dialog.stage.text())
        for widget in [self.dialog.hits, self.dialog.edge, self.dialog.frame,
                       self.dialog.confirm, self.dialog.apply_button, *self.dialog.nudge_buttons]:
            self.assertFalse(widget.isEnabled())
        self.assertIn('Calcul en cours', self.dialog.preview.text())
        self.dialog.busy = False

    def test_real_process_completion_unlocks_review_without_manual_callback(self):
        root = Path(self.temp.name)
        scripts = root / 'script' / 'research'
        scripts.mkdir(parents=True)
        output = root / 'completed'
        code = ('from pathlib import Path\n'
                f'output = Path({str(output)!r})\n'
                'output.mkdir()\n'
                f'(output / "resultat.json").write_text({json.dumps(self.report)!r})\n')
        (scripts / 'complete.py').write_text(code)
        self.dialog.repository = root
        loop = QtCore.QEventLoop()
        self.dialog.process.finished.connect(loop.quit)
        QtCore.QTimer.singleShot(3000, loop.quit)
        self.dialog.start('discovery', 'complete.py', [], output)
        loop.exec()
        self.assertEqual(self.dialog.process.state(), QtCore.QProcess.ProcessState.NotRunning)
        self.assertFalse(self.dialog.busy)
        self.assertEqual(self.dialog.cancel_button.text(), 'Fermer')
        self.assertEqual(self.dialog.groups.rowCount(), 1)
        self.assertNotIn('Calcul en cours', self.dialog.preview.text())
        self.assertFalse(self.dialog.activity.isVisible())
        self.assertIn('Recherche', self.dialog.notice.text())

    def test_restores_completed_refinement_without_recomputing_or_confirming(self):
        root = Path(self.temp.name)
        output = root / 'tmp' / 'repeated-sequence-reviews' / 'previous'
        output.mkdir(parents=True)
        refined = {'status': 'experimental', 'source': str(self.source), 'source_identity': identity(self.source),
                   'outer_bounds': [10, 1900], 'refinement': {'status': 'experimental'},
                   'coordinate_basis': 'FFmpeg decoded source frame index; editor mapping unverified',
                   'source_motif_limits': [{'motif_start_decoded_frame': start, 'motif_end_decoded_frame_exclusive': start + 75}
                                          for start in [125, 500, 1000, 1500]]}
        (output / 'manifest.json').write_text(json.dumps(refined))
        self.dialog.repository = root
        with patch.object(self.dialog.process, 'start') as start:
            self.dialog.restore_completed_refinement()
        start.assert_not_called()
        self.assertEqual(self.dialog.hits.count(), 4)
        self.assertIn('retrouvé', self.dialog.notice.text())
        self.assertFalse(self.dialog.busy)
        self.assertTrue(self.dialog.confirm.isEnabled())
        self.assertFalse(self.dialog.confirm.isChecked())
        self.assertFalse(self.dialog.apply_button.isEnabled())
        self.assertIn('Affinement terminé', self.dialog.stage.text())
        self.assertTrue(self.dialog.edge.isEnabled())

    def test_hidden_groups_keep_their_original_candidate_number(self):
        valid = self.report['candidates'][0]
        invalid = {'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 2}
                                  for value in range(1, 61, 4)]}
        self.report['candidates'] = [invalid, valid]
        self.path.write_text(json.dumps(self.report))
        self.dialog.load_report(self.path)
        self.assertEqual(self.dialog.groups.rowCount(), 1)
        self.assertEqual(self.dialog.groups.item(0, 0).text(), '2')
        self.dialog.groups.selectRow(0)
        with patch.object(self.dialog, 'start') as start:
            self.dialog.refine_group()
        args = start.call_args.args[2]
        self.assertEqual(args[args.index('--candidate') + 1], '2')

    def test_cut_review_previews_adjacent_kept_and_discarded_frames(self):
        refined = {'status': 'experimental', 'source': str(self.source), 'source_identity': identity(self.source),
                   'outer_bounds': [10, 1900], 'refinement': {'status': 'experimental'},
                   'coordinate_basis': 'FFmpeg decoded source frame index; editor mapping unverified',
                   'source_motif_limits': [{'motif_start_decoded_frame': start, 'motif_end_decoded_frame_exclusive': start + 75}
                                          for start in [125, 500, 1000, 1500]]}
        self.dialog.display_refinement(refined)
        self.assertIn('Départ proposé 1', self.dialog.hits.item(0).text())
        self.assertEqual(self.dialog.edge.currentText(), 'Dernière image conservée (OUT)')
        self.assertEqual(self.dialog.frame.value(), 124)
        self.dialog.edge.setCurrentIndex(1)
        self.assertEqual(self.dialog.frame.value(), 125)
        self.dialog.hits.setCurrentRow(1)
        self.assertIn('Reprise proposée 1', self.dialog.hits.item(1).text())
        self.assertEqual(self.dialog.edge.currentText(), 'Première image conservée (IN)')
        self.assertEqual(self.dialog.frame.value(), 575)
        self.dialog.edge.setCurrentIndex(0)
        self.assertEqual(self.dialog.frame.value(), 574)

    def test_stage_progress_handles_split_output_and_shows_elapsed_time(self):
        self.dialog.busy = True
        self.dialog.elapsed.start()
        first = b'REVIEW_STAGE {"step": 2, "label": '
        second = b'"Preparation"}\n'
        with patch.object(self.dialog.process, 'readAllStandardOutput', side_effect=[first, second]):
            self.dialog.progress()
            self.dialog.progress()
        self.assertEqual(self.dialog.activity.maximum(), 3)
        self.assertEqual(self.dialog.activity.value(), 1)
        self.assertIn('Preparation', self.dialog.stage.text())
        self.assertIn('écoulé', self.dialog.stage.text())
        self.dialog.busy = False

    def test_two_role_families_with_outside_support_can_be_chosen_and_refined(self):
        self.dialog.bounds = (1750, 4874)
        self.report['candidates'] = [
            {'classification': 'unverified_repeated_visual_sequence',
             'grouping': 'each_occurrence_directly_matches_one_anchor',
             'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 2} for value in times]}
            for times in [[25, 85, 145], [55, 115, 175]]]
        self.path.write_text(json.dumps(self.report))
        self.dialog.load_report(self.path)
        # Neither has the three inside occurrences required by common-motif mode.
        self.assertEqual(self.dialog.groups.rowCount(), 0)
        self.dialog.paired.setChecked(True)
        self.assertEqual(self.dialog.groups.rowCount(), 2)
        self.assertFalse(self.dialog.refine_button.isEnabled())
        self.dialog.departure_family.setCurrentIndex(1)
        self.dialog.resume_family.setCurrentIndex(2)
        self.assertTrue(self.dialog.refine_button.isEnabled())
        with patch.object(self.dialog, 'start') as start:
            self.dialog.refine_group()
        args = start.call_args.args[2]
        self.assertNotIn('--candidate', args)
        self.assertEqual(args[args.index('--departure-candidate') + 1], '1')
        self.assertEqual(args[args.index('--resume-candidate') + 1], '2')
        self.assertFalse(self.dialog.confirm.isChecked())

    def test_role_families_cannot_be_identical_or_reversed(self):
        self.dialog.bounds = (1750, 4874)
        self.report['candidates'] = [
            {'grouping': 'each_occurrence_directly_matches_one_anchor',
             'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 2} for value in times]}
            for times in [[25, 85, 145], [55, 115, 175]]]
        self.path.write_text(json.dumps(self.report))
        self.dialog.load_report(self.path)
        self.dialog.paired.setChecked(True)
        self.dialog.departure_family.setCurrentIndex(1)
        self.dialog.resume_family.setCurrentIndex(1)
        self.assertFalse(self.dialog.refine_button.isEnabled())
        self.dialog.departure_family.setCurrentIndex(2)
        self.dialog.resume_family.setCurrentIndex(1)
        self.assertFalse(self.dialog.refine_button.isEnabled())

    def test_leaving_expert_mode_clears_hidden_group_instructions(self):
        self.dialog.load_report(self.path)
        self.assertIn('groupes affichés', self.dialog.notice.text())
        self.dialog.expert.setChecked(False)
        self.assertTrue(self.dialog.groups.isHidden())
        self.assertNotIn('groupes affichés', self.dialog.notice.text())
        self.assertIn('Recherche terminée', self.dialog.notice.text())

    def test_ambiguous_hypothesis_is_visible_in_idle_preview_not_only_tooltip(self):
        self.dialog.expert.setChecked(False)
        self.dialog.bounds = (0, 20000)
        self.report['candidates'] = [
            {'occurrences': [{'core_start_seconds': value, 'core_end_seconds': value + 2}
                             for value in starts]}
            for starts in [[100,200,300,400], [110,210,310,410]]]
        self.path.write_text(json.dumps(self.report))
        self.dialog.preview.setText('Calcul en cours…')
        self.dialog.load_report(self.path)
        self.assertFalse(self.dialog.refine_button.isEnabled())
        self.assertIn('même soutien', self.dialog.stage.text())
        self.assertIn('même soutien', self.dialog.preview.text())
        self.assertNotIn('Calcul en cours', self.dialog.preview.text())
        self.assertIn('Recherche terminée', self.dialog.notice.text())

    def test_starting_new_research_removes_old_preview_positions(self):
        self.dialog.load_report(self.path)
        self.dialog.groups.selectRow(0)
        self.assertTrue(self.dialog.preview_rows)
        with patch.object(self.dialog.process, 'start'):
            self.dialog.start('discovery', 'unused.py', [], Path(self.temp.name) / 'new-output')
        self.assertEqual(self.dialog.preview_rows, [])
        self.assertEqual(self.dialog.hits.count(), 0)
        self.assertIn('Calcul en cours', self.dialog.preview.text())
        self.dialog.busy = False
