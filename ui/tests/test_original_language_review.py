import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

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

    def test_validated_vf_overrides_foreign_evidence_and_is_saved_without_question(self):
        self.writer.vidb_result = self.result("en", "foreign")
        self.writer.vidb_result["metadata"]["language_version"] = "VF"
        choose = Mock(side_effect=AssertionError("validated choice must be reused"))
        self.assertTrue(prepare_track_selection(self.monitor, self.path, choose))
        saved = json.loads(self.path.read_text())["track_selection"]
        self.assertEqual("french_only", saved["mode"])
        self.assertEqual("VF", saved["evidence"]["language_version"])

    def test_existing_selection_has_priority_over_a_new_catalogue_version(self):
        self.document["track_selection"] = {"scope": selection_scope(self.document),
                                            "mode": "original_with_subtitles"}
        self.save_document()
        before = self.path.read_bytes()
        self.writer.vidb_result = self.result()
        self.writer.vidb_result["metadata"]["language_version"] = "VF"
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual("original_with_subtitles", self.session.track_selection["mode"])

    def test_retry_refreshes_catalogue_vf_after_the_same_record_is_corrected_to_vmst(self):
        initial = self.result("en", "foreign")
        initial["metadata"]["language_version"] = "VF"
        self.writer.vidb_result = initial
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        self.assertEqual("french_only", self.session.track_selection["mode"])

        corrected = self.result("en", "foreign")
        corrected["metadata"]["language_version"] = "VMST"
        self.writer.vidb_link = Mock()
        self.writer.vidb_link.identify.return_value = corrected
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))

        self.assertEqual({"refresh": True}, self.writer.vidb_link.identify.call_args.kwargs)
        saved = json.loads(self.path.read_text())["track_selection"]
        self.assertEqual("original_with_subtitles", saved["mode"])
        self.assertEqual("VMST", saved["evidence"]["language_version"])
        self.assertEqual(saved, self.session.track_selection)

    def test_foreign_keeps_original_route(self):
        self.writer.vidb_result = self.result("en", "foreign")
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        self.assertEqual("original_with_subtitles", self.session.track_selection["mode"])

    def test_uncertain_language_prefers_vmst_if_the_used_source_really_has_the_tracks(self):
        self.monitor.media_inspection_client = Mock()
        self.monitor.media_inspection_client.inspect.return_value = {"inspection": {
            "audio_tracks": [{"language": "fra"}, {"language": "qaa"}],
            "subtitle_tracks": [{"language": "fra"}]}}
        choose = Mock(side_effect=AssertionError("VMST should be preferred without dropping available tracks"))
        self.assertTrue(prepare_track_selection(self.monitor, self.path, choose))
        self.assertEqual("original_with_subtitles", self.session.track_selection["mode"])
        self.assertEqual("source_default", self.session.track_selection["confirmed_by"])
        self.assertEqual("prefer_vmst_when_uncertain", self.session.track_selection["evidence"]["policy"])

    def test_forced_only_subtitles_do_not_silently_default_to_vmst(self):
        self.monitor.media_inspection_client = Mock()
        self.monitor.media_inspection_client.inspect.return_value = {"inspection": {
            "audio_tracks": [{"language": "fra"}, {"language": "qaa"}],
            "subtitle_tracks": [{"language": "fra", "forced": True}]}}
        choose = Mock(return_value=None)
        self.assertFalse(prepare_track_selection(self.monitor, self.path, choose))
        choose.assert_called_once()

    def catalogue_vf_with_unknown_original_language(self):
        result = self.result()
        result["metadata"] = {"language_version": "VF", "original_language_evidence": {"status": "unknown"}}
        self.writer.vidb_result = result
        return result

    def inspect_vmst_source(self):
        self.monitor.media_inspection_client = Mock()
        self.monitor.media_inspection_client.inspect.return_value = {"inspection": {
            "audio_tracks": [{"language": "fra"}, {"language": "fra", "visual_impaired": True},
                             {"language": "qaa"}],
            "subtitle_tracks": [{"language": "fra", "hearing_impaired": True}, {"language": "fra"}]}}

    def test_catalogue_vf_with_unknown_language_requires_confirmation_with_vf_preselected(self):
        self.catalogue_vf_with_unknown_original_language()
        self.inspect_vmst_source()
        module = "video_encoder_ui.original_language_review"
        with patch(f"{module}.confirm_copy_version", return_value="french_only") as confirm:
            self.assertTrue(prepare_track_selection(self.monitor, self.path))
        confirm.assert_called_once_with(self.monitor, [], "french_only", catalogue_hint=True)
        saved = json.loads(self.path.read_text())["track_selection"]
        self.assertEqual("french_only", saved["mode"])
        self.assertEqual("user", saved["confirmed_by"])

    def test_catalogue_vf_without_original_language_evidence_is_also_only_a_hint(self):
        result = self.catalogue_vf_with_unknown_original_language()
        result["metadata"].pop("original_language_evidence")
        self.assertIsNone(proposed_mode(result))

    def test_cancelling_catalogue_vf_confirmation_leaves_previous_automatic_choice_intact(self):
        self.catalogue_vf_with_unknown_original_language()
        self.document["track_selection"] = {"scope": selection_scope(self.document),
                                            "mode": "original_with_subtitles", "confirmed_by": "source_default"}
        self.save_document()
        before = self.path.read_bytes()
        module = "video_encoder_ui.original_language_review"
        with patch(f"{module}.confirm_copy_version", return_value=None) as confirm:
            self.assertFalse(prepare_track_selection(self.monitor, self.path))
        confirm.assert_called_once_with(self.monitor, [], "french_only", catalogue_hint=True)
        self.assertEqual(before, self.path.read_bytes())

    def test_a_french_original_is_not_mistaken_for_vmst_because_it_has_a_qaa_track(self):
        self.writer.vidb_result = self.result()
        self.writer.vidb_result["metadata"]["language_version"] = "VF"
        self.inspect_vmst_source()
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        self.assertEqual("french_only", self.session.track_selection["mode"])
        self.monitor.media_inspection_client.inspect.assert_not_called()

    def test_an_explicit_saved_vf_is_preserved_despite_the_available_vmst_tracks(self):
        self.catalogue_vf_with_unknown_original_language()
        self.inspect_vmst_source()
        self.document["track_selection"] = {"scope": selection_scope(self.document),
                                            "mode": "french_only", "confirmed_by": "user"}
        self.save_document()
        before = self.path.read_bytes()
        self.assertTrue(prepare_track_selection(self.monitor, self.path, Mock()))
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual("french_only", self.session.track_selection["mode"])
        self.monitor.media_inspection_client.inspect.assert_not_called()

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
