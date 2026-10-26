import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import vidb_montage_review as review
from video_encoder_ui.vidb_project_link import VidbProjectLink


class VidbUnsavedMontageTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = Path(self.directory.name) / "vidb.json"
        self.config.write_text(json.dumps({"url": "https://vidb.test", "token": "a" * 64}))
        self.source = Path("/commun/to_be_cut/Nouveau film.m2t")
        self.session = SimpleNamespace(sources=[SimpleNamespace(path=self.source)], segments=[object()])
        self.url = "https://vidb.test/encoder_projects/catalogue"
        self.calls = []

        def transport(_config, payload):
            self.calls.append(payload["project"])
            if len(self.calls) == 1:
                return {"status": "unmatched", "review_url": self.url}
            return self.identified(payload["project"]["project_id"])

        self.writer = SimpleNamespace(vidb_link=VidbProjectLink(self.config, transport=transport))

    def identified(self, project_id):
        return {"status": "identified", "binding": {"project_id": project_id, "record_id": 123,
                "binding_token": "signed"}, "review_url": self.url,
                "metadata": {"record_kind": "standalone_video", "french_title": "Nouveau film"}}

    def identify(self):
        return review.review_montage_identification(
            None, self.session, self.source, Path("/videos/Nouveau film.json"), self.writer)

    def test_unsaved_montage_opens_directly_and_retains_binding_without_writing_a_project(self):
        segment = self.session.segments[0]
        with patch.object(review, "open_vidb_modal", return_value=True) as opened:
            self.assertTrue(self.identify())
        opened.assert_called_once_with(None, self.url)
        self.assertEqual(2, len(self.calls))
        self.assertEqual(self.calls[0]["project_id"], self.calls[1]["project_id"])
        self.assertEqual(123, self.session.vidb["record_id"])
        self.assertNotIn("metadata", self.session.vidb)
        self.assertIs(segment, self.session.segments[0])
        self.assertEqual([self.config], list(Path(self.directory.name).iterdir()))

    def test_already_identified_montage_still_opens_its_review_page(self):
        self.writer.vidb_link.transport = lambda _config, payload: self.identified(payload["project"]["project_id"])
        with patch.object(review, "open_vidb_modal", return_value=True) as opened:
            self.assertTrue(self.identify())
        opened.assert_called_once_with(None, self.url)

    def test_unavailable_service_reports_the_problem_instead_of_silently_returning(self):
        self.writer.vidb_link.transport = Mock(side_effect=OSError("offline"))
        with patch.object(review.QtWidgets.QMessageBox, "information") as information, \
             patch.object(review, "open_vidb_modal") as opened:
            self.assertFalse(self.identify())
        information.assert_called_once()
        self.assertIn("indisponible", information.call_args.args[2])
        opened.assert_not_called()

    def test_unconfigured_bridge_is_reported(self):
        self.config.unlink()
        with patch.object(review.QtWidgets.QMessageBox, "information") as information:
            self.assertFalse(self.identify())
        self.assertIn("configuration", information.call_args.args[2])

    def test_browser_failure_keeps_the_montage_and_does_not_reidentify(self):
        with patch.object(review, "open_vidb_modal", return_value=False):
            self.assertFalse(self.identify())
        self.assertEqual(1, len(self.calls))
        self.assertEqual(1, len(self.session.segments))
