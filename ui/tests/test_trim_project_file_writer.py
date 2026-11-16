import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import Mock
from types import SimpleNamespace

from video_encoder_ui.trim_project_file_writer import (
    TrimProjectFileWriter,
)
from video_encoder_ui.montage_condition import declaration
from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession


class TrimProjectFileWriterTest(unittest.TestCase):
    def test_condition_survives_saving_and_reopening_without_changing_the_binding(self):
        session = TrimSession()
        session.add_source(SourceReference("one", Path("/commun/source.m2t")))
        session.add_segment(SegmentSelection("one", 1, 100))
        session.vidb = {"record_id": 42, "binding_token": "confirmed"}
        session.copy_condition = declaration(session, integrality="incomplete", damage="light", note="Fin manquante")
        document = {"format": "video_encoder.trim_project", "version": 2,
                    "sources": [{"id": "one", "path": "/commun/source.m2t"}],
                    "timeline": [{"type": "segment", "source_id": "one", "start_frame": 1, "end_frame": 100}]}
        writer = TrimProjectFileWriter(Mock(convert=Mock(return_value=document)))
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "montage.json"
            writer.save(session, destination)
            restored = TrimProjectFileReader().load(destination)
        self.assertEqual(session.copy_condition, restored.copy_condition)
        self.assertEqual(session.vidb, restored.vidb)

    def test_invalid_condition_is_rejected_before_touching_an_existing_project(self):
        session = SimpleNamespace(copy_condition={"damage": "bad"})
        writer = TrimProjectFileWriter(Mock(convert=Mock(return_value={})))
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "montage.json"
            destination.write_text("original", encoding="utf-8")
            with self.assertRaises(ValueError):
                writer.save(session, destination)
            self.assertEqual("original", destination.read_text(encoding="utf-8"))

    def test_writes_the_canonical_project_returned_by_ruby(self):
        document = {
            "format": "video_encoder.trim_project",
            "version": 1,
            "timeline": [
                {
                    "type": "segment",
                    "source": "/commun/source-a.m2t",
                    "start_frame": 1500,
                    "end_frame": 2999
                }
            ]
        }

        bridge = Mock()
        bridge.convert.return_value = document

        writer = TrimProjectFileWriter(bridge)

        with tempfile.TemporaryDirectory() as directory:
            destination = (
                Path(directory)
                / "montage.json"
            )

            result = writer.save(
                SimpleNamespace(analysis_workspaces=[]),
                destination
            )

            self.assertEqual(result, destination)
            saved = json.loads(destination.read_text(encoding="utf-8"))
            self.assertEqual({key: value for key, value in saved.items() if key != "project_id"}, document)
            self.assertEqual(uuid.UUID(saved["project_id"]).version, 4)


if __name__ == "__main__":
    unittest.main()
