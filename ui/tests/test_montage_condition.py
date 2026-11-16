import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from video_encoder_ui.montage_condition import checked_condition, declaration, needs_review
from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession


class MontageConditionTest(unittest.TestCase):
    def setUp(self):
        self.session = TrimSession()
        self.session.add_source(SourceReference("one", Path("/commun/émission.m2t")))
        self.session.add_segment(SegmentSelection("one", 25, 250))

    def test_default_is_complete_and_undamaged_but_requires_a_first_confirmation(self):
        self.assertTrue(needs_review(self.session))
        self.session.copy_condition = declaration(self.session)
        self.assertFalse(needs_review(self.session))
        self.assertEqual("complete", self.session.copy_condition["integrality"])
        self.assertEqual("none", self.session.copy_condition["damage"])

    def test_damage_does_not_imply_incompleteness_or_a_retained_portion(self):
        value = declaration(self.session, damage="severe", note="Son abîmé, durée conservée : 23 min")
        self.assertEqual("complete", value["integrality"])
        self.assertEqual("unknown", value["retained_portion"])
        self.assertNotIn("retained_duration_seconds", value)

    def test_incomplete_without_specifying_beginning_or_end_and_combined_damage(self):
        value = declaration(self.session, integrality="incomplete", damage="light", note="Coupures")
        self.assertEqual("unknown", value["retained_portion"])
        self.assertEqual("light", value["damage"])

    def test_only_sources_retained_in_the_montage_trigger_another_review(self):
        self.session.copy_condition = declaration(self.session)
        self.session.add_source(SourceReference("two", Path("/commun/autre.m2t")))
        self.assertFalse(needs_review(self.session))
        self.session.add_segment(SegmentSelection("two", 1, 100))
        self.assertTrue(needs_review(self.session))

    def test_validation_rejects_an_unrelated_source_and_overlong_notes(self):
        for change in ({"affected_source_paths": ["/commun/autre.m2t"]}, {"note": "x" * 2001},
                       {"retained_portion": "end"}, {"damage": "bad"}, {"declared_at": "yesterday"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                checked_condition({**declaration(self.session), **change})

    def test_loading_an_old_project_does_not_manufacture_a_declaration(self):
        session = self.load_document(None)
        self.assertIsNone(getattr(session, "copy_condition", None))
        self.assertTrue(needs_review(session))

    def test_loading_preserves_a_declaration_and_its_source_and_note(self):
        value = declaration(self.session, integrality="incomplete", retained_portion="end",
                            note="Fin seulement", affected_source_paths=["/commun/émission.m2t"])
        loaded = self.load_document(value)
        self.assertEqual(value, loaded.copy_condition)
        self.assertFalse(needs_review(loaded))

    def test_reencoding_preserves_the_condition_without_sharing_mutable_notes(self):
        from video_encoder_ui.reencode_project import clone_session

        self.session.copy_condition = declaration(self.session, integrality="incomplete", note="Coupure")
        clone = clone_session(self.session, {"inspections": {}}, "french_only")
        self.assertEqual(self.session.copy_condition, clone.copy_condition)
        clone.copy_condition["note"] = "Précision"
        self.assertEqual("Coupure", self.session.copy_condition["note"])

    def load_document(self, condition):
        document = {"format": "video_encoder.trim_project", "version": 2,
                    "sources": [{"id": "one", "path": "/commun/émission.m2t"}],
                    "timeline": [{"type": "segment", "source_id": "one", "start_frame": 25, "end_frame": 250}]}
        if condition is not None:
            document["copy_condition"] = condition
        with TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return TrimProjectFileReader().load(path)
