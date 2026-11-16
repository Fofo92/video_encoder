import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession


class VidbLaunchPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.session = TrimSession()
        self.session.add_source(SourceReference("one", Path("/commun/source.m2t")))
        self.session.add_segment(SegmentSelection("one", 1, 100))
        self.session.vidb_launch = "pending-ticket"
        self.document = {"format": "video_encoder.trim_project", "version": 2,
                         "sources": [{"id": "one", "path": "/commun/source.m2t"}],
                         "timeline": [{"type": "segment", "source_id": "one", "start_frame": 1, "end_frame": 100}]}

    def test_a_pending_choice_is_saved_and_restored_if_identification_is_temporarily_unavailable(self):
        link = Mock(identify=Mock(return_value={"status": "pending", "reason": "network"}))
        writer = TrimProjectFileWriter(Mock(convert=Mock(return_value=self.document)), vidb_link=link)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            writer.save(self.session, path)
            loaded = TrimProjectFileReader().load(path)
        self.assertEqual("pending-ticket", loaded.vidb_launch)
        self.assertEqual(self.session.project_id, loaded.project_id)
        self.assertEqual("pending-ticket", link.identify.call_args.args[0]["vidb_launch"])

    def test_successful_binding_removes_the_temporary_ticket_but_keeps_the_signed_binding(self):
        link = Mock(identify=Mock(return_value={"status": "identified", "record_id": 42, "binding_token": "binding"}))
        writer = TrimProjectFileWriter(Mock(convert=Mock(return_value=self.document)), vidb_link=link)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            writer.save(self.session, path)
            document = json.loads(path.read_text())
        self.assertNotIn("vidb_launch", document)
        self.assertIsNone(self.session.vidb_launch)
        self.assertEqual(42, document["vidb"]["record_id"])
        self.assertEqual("binding", document["vidb"]["binding_token"])

    def test_a_reencoding_clone_does_not_lose_a_pending_explicit_record_choice(self):
        from video_encoder_ui.reencode_project import clone_session

        clone = clone_session(self.session, {"inspections": {}}, "french_only")
        self.assertEqual("pending-ticket", clone.vidb_launch)

    def test_a_corrupted_pending_choice_is_rejected_instead_of_losing_the_explicit_record(self):
        document = {**self.document, "vidb_launch": ""}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(json.dumps(document))
            with self.assertRaises(ValueError):
                TrimProjectFileReader().load(path)
