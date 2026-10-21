import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from video_encoder_ui.graphic_review import (observation_manifest, proposed_graphic_session, load_graphic_review)
from video_encoder_ui.repeated_sequence_review import identity

try:
    from PySide6 import QtCore,QtGui,QtWidgets
    from video_encoder_ui.repeated_sequence_dialog import RepeatedSequenceDialog
except ModuleNotFoundError:
    QtWidgets=None


class GraphicFixture:
    def fixture(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.m2t';self.source.write_bytes(b'source')
        self.bounds=(10,1900)
        self.output=self.root/'tmp/repeated-sequence-reviews/graphic';self.output.mkdir(parents=True)
        manifest=self.output/'raccords/frame-map.json';manifest.parent.mkdir();manifest.write_text('{}')
        self.report={'status':'candidate_raccords','review_origin':'graphic_hypotheses','fps':25,
                     'source':str(self.source),'source_identity':identity(self.source),'outer_bounds':list(self.bounds),
                     'review_manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),
                     'raccords':[{'candidate_role':role,'group_index':index//2+1,'status':'candidate_raccord',
                                  'candidate_transition_decoded_frame':frame,
                                  'candidate_kept_decoded_frame':frame-1 if role=='departure' else frame,
                                  'kept_frame_meaning':'last_kept' if role=='departure' else 'first_kept'}
                                 for index,(role,frame) in enumerate([('departure',125),('resume',500),
                                                                   ('departure',1000),('resume',1500)])]}
        self.pipeline={'status':'ready_for_review','source':str(self.source),'source_identity':identity(self.source),
                       'exterior_bounds_frames_inclusive':list(self.bounds)}
        self.save()

    def save(self):
        (self.output/'pipeline.json').write_text(json.dumps(self.pipeline))
        (self.output/'raccords.json').write_text(json.dumps(self.report))

    def teacher(self):
        directory=self.root/'tmp/repeated-sequence-reviews/observations';directory.mkdir()
        windows=[]
        for i,first in enumerate([100,500]):
            name=f'clip-{i}.mp4';(directory/name).write_bytes(b'clip')
            windows.append({'name':name,'first_decoded_frame':first,'end_decoded_frame_exclusive':first+50})
        path=directory/'manifest.json'
        path.write_text(json.dumps({'source':str(self.source),'source_identity':identity(self.source),
                                    'outer_bounds':list(self.bounds),'windows':windows}))
        return path


class GraphicReviewTest(GraphicFixture,unittest.TestCase):
    def setUp(self):self.fixture()

    def test_format_proposals_use_the_same_explicit_confirmation_and_source_checks(self):
        self.report['review_origin']='format_hypotheses';self.save()
        _,report=load_graphic_review(self.output/'pipeline.json',self.source,self.bounds)
        with self.assertRaises(ValueError):proposed_graphic_session(report,self.source,*self.bounds)
        session=proposed_graphic_session(report,self.source,*self.bounds,confirmed=True)
        self.assertEqual([(r.start_frame,r.end_frame) for r in session.segments],[(10,124),(500,999),(1500,1900)])
        self.source.write_bytes(b'changed')
        with self.assertRaises(ValueError):proposed_graphic_session(report,self.source,*self.bounds,confirmed=True)

    def test_geometric_review_does_not_accept_segments_before_confirmation(self):
        pipeline,report=load_graphic_review(self.output/'pipeline.json',self.source,self.bounds)
        with self.assertRaises(ValueError):proposed_graphic_session(report,self.source,*self.bounds)
        session=proposed_graphic_session(report,self.source,*self.bounds,confirmed=True)
        self.assertEqual([(r.start_frame,r.end_frame) for r in session.segments],[(10,124),(500,999),(1500,1900)])
        self.assertEqual(self.source.read_bytes(),b'source')

    def test_source_bounds_roles_and_off_by_one_mismatch_are_rejected(self):
        for key,value in [('candidate_role','resume'),('candidate_kept_decoded_frame',125)]:
            report=copy.deepcopy(self.report);report['raccords'][0][key]=value
            with self.assertRaises(ValueError):proposed_graphic_session(report,self.source,*self.bounds,confirmed=True)
        with self.assertRaises(ValueError):proposed_graphic_session(self.report,self.source,11,1900,confirmed=True)
        self.source.write_bytes(b'changed')
        with self.assertRaises(ValueError):load_graphic_review(self.output/'pipeline.json',self.source,self.bounds)

    def test_manifest_change_is_rejected_and_unresolved_output_cannot_be_accepted(self):
        self.report['status']='unresolved_raccords';self.report['raccords'][0]={'candidate_role':'departure','group_index':1,'status':'unresolved_no_transition'}
        self.pipeline['status']='needs_review';self.save()
        _,report=load_graphic_review(self.output/'pipeline.json',self.source,self.bounds)
        with self.assertRaises(ValueError):proposed_graphic_session(report,self.source,*self.bounds,confirmed=True)
        (self.output/'raccords/frame-map.json').write_text('changed')
        with self.assertRaises(ValueError):load_graphic_review(self.output/'pipeline.json',self.source,self.bounds)

    def test_available_observations_require_current_source_bounds_and_local_files(self):
        path=self.teacher()
        self.assertEqual(observation_manifest(self.root,self.source,self.bounds),path)
        self.assertEqual(observation_manifest(self.root,self.source,(11,1900)),path)
        self.assertIsNone(observation_manifest(self.root,self.source,(101,1900)))
        (path.parent/'clip-0.mp4').unlink()
        self.assertIsNone(observation_manifest(self.root,self.source,self.bounds))


@unittest.skipIf(QtWidgets is None,'PySide6 unavailable')
class GraphicDialogTest(GraphicFixture,unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.fixture()
        image=QtGui.QImage(32,18,QtGui.QImage.Format.Format_RGB32);image.fill(QtCore.Qt.GlobalColor.blue)
        self.frame_source=SimpleNamespace(length=2000,frame_at=lambda position:(image,position,1))
        self.dialog=RepeatedSequenceDialog(self.source,self.bounds,self.frame_source)
        self.dialog.repository=self.root;self.addCleanup(self.dialog.reject)

    def test_format_result_loads_without_group_selection_or_automatic_acceptance(self):
        self.report['review_origin']='format_hypotheses';self.pipeline['preparation_method']='format_hypotheses'
        self.save();self.dialog.load_report(self.output/'raccords.json')
        self.assertEqual(self.dialog.hits.count(),4)
        self.assertFalse(self.dialog.confirm.isChecked())
        self.assertFalse(self.dialog.apply_button.isEnabled())
        self.assertIsNone(self.dialog.session)

    def test_prepare_uses_existing_observations_without_group_or_detector_choice(self):
        teacher=self.teacher();self.dialog.refresh_observations();self.dialog.update_actions()
        self.assertTrue(self.dialog.refine_button.isEnabled())
        with patch.object(self.dialog,'start') as start:self.dialog.refine_group()
        task,script,args,output=start.call_args.args
        self.assertEqual((task,script),('graphic','prepare_graphic_review.py'))
        self.assertEqual(args[args.index('--observation-manifest')+1],str(teacher))
        self.assertNotIn('--candidate',args);self.assertNotIn('--edge-mode',args)
        self.assertFalse(self.dialog.confirm.isChecked())

    def test_kept_and_excluded_previews_and_explicit_apply(self):
        self.pipeline['reused_scan_from']='previous/report.json'
        self.pipeline['reused_review_from']='previous/raccords'
        self.save()
        self.dialog.display_graphic_review(self.output/'pipeline.json')
        self.assertIn('Scan réutilisé',self.dialog.notice.text())
        self.assertIn('Extraits natifs réutilisés',self.dialog.notice.text())
        self.assertFalse(self.dialog.apply_button.isEnabled());self.assertFalse(self.dialog.confirm.isChecked())
        self.assertEqual(self.dialog.frame.value(),124)
        self.dialog.edge.setCurrentIndex(1);self.assertEqual(self.dialog.frame.value(),125)
        self.dialog.hits.setCurrentRow(1);self.assertEqual(self.dialog.frame.value(),500)
        self.dialog.edge.setCurrentIndex(0);self.assertEqual(self.dialog.frame.value(),499)
        self.dialog.confirm.setChecked(True);self.assertTrue(self.dialog.apply_button.isEnabled())
        self.dialog.apply_segments();self.assertEqual(self.dialog.result(),QtWidgets.QDialog.DialogCode.Accepted)
        self.assertEqual([(r.start_frame,r.end_frame) for r in self.dialog.session.segments],[(10,124),(500,999),(1500,1900)])

    def test_partial_result_shows_correct_resume_role_but_cannot_replace_montage(self):
        self.pipeline['status']='needs_review';self.report['status']='unresolved_raccords'
        self.report['raccords'][0]={'candidate_role':'departure','group_index':1,'status':'unresolved_no_transition'}
        self.save();self.dialog.display_graphic_review(self.output/'pipeline.json')
        self.assertIn('Reprise proposée 1',self.dialog.hits.item(0).text())
        self.assertEqual(self.dialog.frame.value(),500)
        self.assertFalse(self.dialog.confirm.isEnabled());self.assertFalse(self.dialog.apply_button.isEnabled())
        self.assertIsNone(self.dialog.session);self.assertIn('non résolus',self.dialog.stage.text())

    def test_empty_grouping_retains_diagnostics_and_does_not_claim_no_advertisements(self):
        self.pipeline.update(status='needs_review',reason='Aucun groupe exploitable.')
        self.save();(self.output/'raccords.json').unlink()
        self.dialog.display_graphic_review(self.output/'pipeline.json')
        self.assertEqual(self.dialog.hits.count(),0);self.assertFalse(self.dialog.apply_button.isEnabled())
        self.assertFalse(self.dialog.busy);self.assertIn('non résolus',self.dialog.stage.text())
        self.assertFalse(self.dialog.copy_diagnostic.isHidden())

    def test_real_child_completion_loads_graphic_review_without_extra_action(self):
        scripts=self.root/'script/research';scripts.mkdir(parents=True)
        (scripts/'complete.py').write_text('pass\n')
        loop=QtCore.QEventLoop();self.dialog.process.finished.connect(loop.quit)
        QtCore.QTimer.singleShot(3000,loop.quit)
        self.dialog.start('graphic','complete.py',[],self.output);loop.exec()
        self.assertFalse(self.dialog.busy);self.assertEqual(self.dialog.hits.count(),4)
        self.assertFalse(self.dialog.confirm.isChecked());self.assertFalse(self.dialog.apply_button.isEnabled())
        self.assertNotIn('Calcul en cours',self.dialog.stage.text())

    def test_old_failure_starts_one_graphic_attempt_and_graphic_failure_does_not_loop(self):
        teacher=self.teacher();self.dialog.task='refinement';self.dialog.output=teacher.parent;self.dialog.busy=True
        with patch.object(self.dialog,'start') as start:
            self.dialog.process_finished(1,QtCore.QProcess.ExitStatus.NormalExit)
        self.assertEqual(start.call_args.args[0],'graphic')
        self.dialog.task='graphic';self.dialog.busy=True
        with patch.object(self.dialog,'start') as start,patch('video_encoder_ui.repeated_sequence_dialog.QtWidgets.QMessageBox.warning'):
            self.dialog.process_finished(1,QtCore.QProcess.ExitStatus.NormalExit)
        start.assert_not_called();self.assertIsNone(self.dialog.session)

    def test_four_stage_progress_and_reopen_do_not_auto_confirm(self):
        self.dialog.busy=True;self.dialog.task='graphic';self.dialog.elapsed.start()
        message=b'REVIEW_STAGE {"step":4,"total":4,"label":"Raccords"}\n'
        with patch.object(self.dialog.process,'readAllStandardOutput',return_value=message):self.dialog.progress()
        self.assertEqual(self.dialog.activity.maximum(),4);self.assertEqual(self.dialog.activity.value(),3)
        self.assertIn('écoulé',self.dialog.stage.text())
        final_stage=b'REVIEW_STAGE {"step":5,"total":5,"label":"Raccords"}\n'
        with patch.object(self.dialog.process,'readAllStandardOutput',return_value=final_stage):self.dialog.progress()
        self.assertEqual(self.dialog.activity.maximum(),5)
        self.assertEqual(self.dialog.activity.value(),4)
        progress=b'REVIEW_PROGRESS {"sampled_seconds":123.4}\n'
        with patch.object(self.dialog.process,'readAllStandardOutput',return_value=progress):self.dialog.progress()
        self.assertIn('00:02:03',self.dialog.stage.text())
        self.dialog.busy=False
        with patch.object(self.dialog.process,'start') as start:self.dialog.restore_completed_refinement()
        start.assert_not_called();self.assertEqual(self.dialog.hits.count(),4)
        self.assertFalse(self.dialog.confirm.isChecked());self.assertFalse(self.dialog.apply_button.isEnabled())


if __name__=='__main__':unittest.main()
