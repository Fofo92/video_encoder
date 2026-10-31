import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest("PySide6 is unavailable")

from video_encoder_ui.montage_duration import confirm_montage_duration
from video_encoder_ui.project_destination import choose_project_output
from video_encoder_ui.proposal_revision import review_proposal
from video_encoder_ui.vidb_project_link import VidbProjectLink


class ProposalRevisionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.monitor = QtWidgets.QWidget()
        self.monitor.trim_session = SimpleNamespace(project_id='project', segments=[SimpleNamespace(start_frame=0, end_frame=62999)])
        self.monitor.frames_per_second = 25
        self.monitor.source_path = Path('/commun/to_be_cut/film.m2t')
        self.monitor.project_path = None
        self.monitor.trim_project_writer = SimpleNamespace(vidb_result=dict(
            status='identified', project_id='project', record_id=1,
            selection_url='https://vidb.test/encoder_projects/local_records?request_token=token',
            metadata={'reference_runtime_minutes': 53}))

    def tearDown(self):
        self.monitor.close()
        self.monitor.deleteLater()

    def test_duration_review_interrupts_the_save_and_keeps_all_segments(self):
        segments = self.monitor.trim_session.segments
        def choose_review(dialog):
            for button in dialog.buttons():
                if button.text() == 'Revoir la proposition vidb…':
                    button.click()
                    return
            self.fail('Missing revision action')
        with patch.object(QtWidgets.QMessageBox, 'exec', choose_review), \
                patch('video_encoder_ui.proposal_revision.review_proposal', return_value=True) as review:
            self.assertFalse(confirm_montage_duration(self.monitor))
        review.assert_called_once_with(self.monitor)
        self.assertIs(segments, self.monitor.trim_session.segments)

    def test_destination_can_be_revisited_and_preserves_the_expected_extension(self):
        def accept_after_revision(dialog):
            review = next(button for button in dialog.findChildren(QtWidgets.QPushButton)
                          if button.text() == 'Revoir la proposition vidb…')
            review.click()
            return QtWidgets.QDialog.DialogCode.Accepted
        with patch.object(QtWidgets.QDialog, 'exec', accept_after_revision), \
                patch('video_encoder_ui.proposal_revision.review_proposal', return_value=True), \
                patch('video_encoder_ui.proposal_revision.revised_destination', return_value=Path('/videos/Correct.mkv')):
            selected, _filter = choose_project_output(self.monitor, Path('/videos/Old.json'))
        self.assertEqual('/videos/Correct.json', selected)

    def test_review_keeps_the_project_identity_and_resets_the_runtime_cache(self):
        self.monitor._runtime_reference = ('old', 53)
        with patch('video_encoder_ui.proposal_revision.review_montage_identification', return_value=True) as review:
            self.assertTrue(review_proposal(self.monitor))
        self.assertIsNone(self.monitor._runtime_reference)
        self.assertIs(self.monitor.trim_session, review.call_args.args[1])
        self.assertEqual(Path('/videos/film.json'), review.call_args.args[3])

    def test_revision_url_is_accepted_only_inside_the_configured_vidb(self):
        response = dict(status='identified', binding=dict(project_id='project', record_id=1, binding_token='signed'),
                        selection_url='https://vidb.test/encoder_projects/local_records?token=1')
        config = {'url': 'https://vidb.test'}
        result = VidbProjectLink.checked_response(config, response, 'project')
        self.assertEqual(response['selection_url'], result['selection_url'])
        response['selection_url'] = 'https://other.test/records/1'
        with self.assertRaises(ValueError):
            VidbProjectLink.checked_response(config, response, 'project')
