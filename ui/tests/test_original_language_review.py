import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.original_language_review import prepare_track_selection, proposed_mode, selection_scope
from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter


class OriginalLanguageReviewTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "film.json"
        self.document = {"format": "video_encoder.trim_project", "version": 2,
                         "project_id": "00000000-0000-4000-8000-000000000042", "vidb": {"record_id": 42},
                         "sources": [{"id": "source", "path": "/commun/film.m2t"}],
                         "timeline": [{"type": "segment", "source_id": "source", "start_frame": 0,
                                       "end_frame": 100}]}
        self.save_document()
        self.session = SimpleNamespace()
        self.writer = SimpleNamespace(vidb_result={"status": "pending"}, vidb_link=None)
        self.status = Mock()
        self.monitor = SimpleNamespace(trim_session=self.session, trim_project_writer=self.writer,
                                       statusBar=lambda: self.status)

    def save_document(self):
        self.path.write_text(json.dumps(self.document), encoding="utf-8")

    @staticmethod
    def result(language="fr", status="french"):
        return {"status": "identified", "project_id": "00000000-0000-4000-8000-000000000042", "record_id": 42,
                "metadata": {"original_language_evidence": {"provider": "tmdb", "status": status,
                                                            "language": language}}}

    def test_external_french_avoids_question_and_persists_decision(self):
        self.writer.vidb_result = self.result()
        choose = Mock(side_effect=AssertionError("no question expected"))
        self.assertTrue(prepare_track_selection(self.monitor, self.path, choose))
        selection = json.loads(self.path.read_text())["track_selection"]
        self.assertEqual("french_only", selection["mode"])
        self.assertEqual("external", selection["confirmed_by"])
        self.assertEqual(selection_scope(self.document), selection["scope"])

    def test_foreign_keeps_original_route(self):
        self.writer.vidb_result = self.result("en", "foreign")
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        self.assertEqual("original_with_subtitles", self.session.track_selection["mode"])

    def test_unknown_requires_and_saves_user_decision(self):
        choose = Mock(return_value="french_only")
        self.assertTrue(prepare_track_selection(self.monitor, self.path, choose))
        choose.assert_called_once_with(self.monitor)
        self.assertEqual("user", self.session.track_selection["confirmed_by"])

    def test_cancel_leaves_file_intact(self):
        before = self.path.read_bytes()
        self.assertFalse(prepare_track_selection(self.monitor, self.path, lambda _: None))
        self.assertEqual(before, self.path.read_bytes())
        self.assertFalse(hasattr(self.session, "track_selection"))

    def test_restored_choice_is_reused_without_network(self):
        self.document["track_selection"] = {"scope": selection_scope(self.document), "mode": "french_only"}
        self.save_document()
        self.writer.vidb_link = Mock(side_effect=AssertionError("no network"))
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        restored = TrimProjectFileReader().load(self.path)
        self.assertEqual("french_only", restored.track_selection["mode"])

    def test_changed_source_requires_new_confirmation(self):
        self.document["track_selection"] = {"scope": selection_scope(self.document), "mode": "french_only"}
        self.document["sources"][0]["path"] = "/commun/another.m2t"
        self.save_document()
        choose = Mock(return_value=None)
        self.assertFalse(prepare_track_selection(self.monitor, self.path, choose))
        choose.assert_called_once()

    def test_changed_record_does_not_use_previous_metadata(self):
        self.writer.vidb_result = self.result()
        self.document["vidb"]["record_id"] = 43
        self.save_document()
        choose = Mock(return_value=None)
        self.assertFalse(prepare_track_selection(self.monitor, self.path, choose))
        choose.assert_called_once()

    def test_restored_metadata_is_refreshed_for_same_binding(self):
        self.writer.vidb_link = Mock()
        self.writer.vidb_link.identify.return_value = self.result()
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        self.writer.vidb_link.identify.assert_called_once()
        self.assertEqual(self.path, self.writer.vidb_link.identify.call_args.args[1])
        self.assertEqual({"refresh": True}, self.writer.vidb_link.identify.call_args.kwargs)
        self.assertEqual("external", self.session.track_selection["confirmed_by"])

    def test_conflicting_evidence_does_not_automatically_drop_original(self):
        self.assertIsNone(proposed_mode(self.result("en", "french")))
        self.assertIsNone(proposed_mode(self.result("fr", "foreign")))

    def test_writer_preserves_valid_selection_and_discards_stale_one(self):
        self.session.project_id = self.document["project_id"]
        self.session.vidb = self.document["vidb"]
        self.session.track_selection = {"scope": selection_scope(self.document), "mode": "french_only"}
        bridge = Mock()
        bridge.convert.return_value = self.document
        writer = TrimProjectFileWriter(bridge)
        writer.save(self.session, self.path)
        self.assertIn("track_selection", json.loads(self.path.read_text()))
        self.session.track_selection["scope"]["record_id"] = 99
        writer.save(self.session, self.path)
        self.assertNotIn("track_selection", json.loads(self.path.read_text()))


if __name__ == "__main__":
    unittest.main()
