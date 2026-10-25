import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import PySide6
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import vidb_project_review as review


class VidbMenuReviewTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'episode.json'
        self.document = {'project_id': 'existing-project', 'vidb': {'status': 'identified'}}
        self.path.write_text(json.dumps(self.document), encoding='utf-8')
        self.url = 'https://vidb.test/encoder_projects/episode?request_token=fresh'
        self.link = Mock()
        self.link.identify.return_value = {'status': 'identified', 'record_id': 123, 'review_url': self.url}
        self.writer = SimpleNamespace(vidb_link=self.link, vidb_result={'status': 'identified'})

    def test_an_identified_project_is_refreshed_and_the_current_completion_link_is_opened(self):
        with patch.object(review.QtGui.QDesktopServices, 'openUrl', return_value=True) as opened:
            self.assertTrue(review.offer_saved_vidb_review(None, self.writer, self.path))
        self.link.identify.assert_called_once_with(self.document, self.path, refresh=True)
        self.assertEqual(self.url, opened.call_args.args[0].toString())
        self.assertEqual(self.document, json.loads(self.path.read_text(encoding='utf-8')))

    def test_a_missing_link_is_reported_instead_of_silently_ignoring_the_menu_action(self):
        self.link.identify.return_value = {'status': 'identified', 'record_id': 123}
        with patch.object(review.QtWidgets.QMessageBox, 'information') as information:
            self.assertFalse(review.offer_saved_vidb_review(None, self.writer, self.path))
        information.assert_called_once()

    def test_an_unreadable_project_offers_the_existing_pending_workflow(self):
        self.path.unlink()
        with patch.object(review, 'offer_vidb_review', return_value=True) as pending:
            self.assertTrue(review.offer_saved_vidb_review(None, self.writer, self.path))
        pending.assert_called_once_with(None, self.writer)
        self.assertEqual('pending', self.writer.vidb_result['status'])

    def test_normal_encoding_still_does_not_open_a_browser_for_an_identified_project(self):
        self.writer.vidb_result = {'status': 'identified', 'review_url': self.url}
        with patch.object(review.QtGui.QDesktopServices, 'openUrl') as opened:
            self.assertTrue(review.offer_vidb_review(None, self.writer, before_encoding=True))
        opened.assert_not_called()
