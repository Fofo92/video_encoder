import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from video_encoder_ui.media_inspection_client import MediaInspectionError
from video_encoder_ui.original_language_review import selection_scope
from video_encoder_ui.reencode_project import prepare_reencode, project_document, suggested_output
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession
from test_track_options import complete_tracks


class ReencodeProjectTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "capture.m2t"
        self.source.write_bytes(b"original transport stream")
        self.project = self.root / "S12 E05 - Marée montante (The Rising Tide).json"
        self.original_video = self.project.with_suffix(".mkv")
        self.original_video.write_bytes(b"existing french-only encoding")
        self.session = TrimSession()
        self.session.add_source(SourceReference("source", self.source))
        self.session.add_segment(SegmentSelection("source", 25, 200))
        self.session.add_segment(SegmentSelection("source", 300, 600))
        self.session.project_id = "00000000-0000-4000-8000-000000000042"
        self.session.vidb = {"record_id": 42}
        self.session.track_selection = {"mode": "french_only", "scope": selection_scope(project_document(self.session))}
        bridge = Mock()
        bridge.convert.side_effect = lambda session: dict(project_document(session), format="video_encoder.trim_project")
        self.writer = TrimProjectFileWriter(bridge)
        self.writer.save(self.session, self.project)
        self.old_project = self.project.read_bytes()
        self.inspector = Mock()
        self.inspector.inspect.return_value = {"inspection": complete_tracks()}
        self.monitor = SimpleNamespace(project_path=self.project, trim_session=self.session,
                                       trim_project_writer=self.writer, media_inspection_client=self.inspector)
        self.report = Mock()

    def prepare(self, mode="original_with_subtitles", output=None):
        self.choose = Mock(return_value=mode)
        self.select_output = Mock(side_effect=lambda _monitor, proposed: output if output is not None else proposed)
        return prepare_reencode(self.monitor, choose=self.choose, select_output=self.select_output, report=self.report)

    def assert_originals_unchanged(self):
        self.assertEqual(self.old_project, self.project.read_bytes())
        self.assertEqual(b"existing french-only encoding", self.original_video.read_bytes())
        self.assertEqual(b"original transport stream", self.source.read_bytes())
        self.assertEqual("french_only", self.session.track_selection["mode"])

    def test_completed_vf_can_be_reencoded_with_vmst_without_replacing_any_existing_file(self):
        result = self.prepare()
        self.assertIsNotNone(result)
        self.assertNotEqual(self.project, result.project_path)
        self.assertIn("VMST", result.output_path.name)
        self.assertFalse(result.output_path.exists())
        self.assertEqual(self.session.segments, result.session.segments)
        self.assertEqual(self.session.project_id, result.session.project_id)
        self.assertEqual({"record_id": 42}, result.session.vidb)
        document = json.loads(result.project_path.read_text())
        self.assertEqual("original_with_subtitles", document["track_selection"]["mode"])
        self.assertEqual("user", document["track_selection"]["confirmed_by"])
        self.assertEqual(selection_scope(document), document["track_selection"]["scope"])
        self.assert_originals_unchanged()
        self.report.assert_not_called()

    def test_cancel_before_destination_does_not_save_a_new_project(self):
        before = set(self.root.iterdir())
        self.assertIsNone(self.prepare(mode=None))
        self.select_output.assert_not_called()
        self.assertEqual(before, set(self.root.iterdir()))
        self.assert_originals_unchanged()

    def test_cancel_destination_does_not_change_the_montage(self):
        selected = Mock(return_value=None)
        result = prepare_reencode(self.monitor, choose=Mock(return_value="original_with_subtitles"),
                                  select_output=selected, report=self.report)
        self.assertIsNone(result)
        self.assert_originals_unchanged()

    def test_an_unavailable_vmst_profile_is_rejected_before_saving(self):
        self.inspector.inspect.return_value["inspection"]["subtitle_tracks"] = []
        self.assertIsNone(self.prepare())
        self.report.assert_called_once()
        self.select_output.assert_not_called()
        self.assert_originals_unchanged()

    def test_an_existing_video_or_project_is_never_replaced(self):
        self.assertIsNone(self.prepare(output=self.original_video))
        self.assert_originals_unchanged()
        output = self.root / "another.mkv"
        output.with_suffix(".json").write_text("another project")
        self.assertIsNone(self.prepare(output=output))
        self.assertEqual("another project", output.with_suffix(".json").read_text())
        self.assert_originals_unchanged()

    def test_missing_source_is_reported_without_falling_back_to_the_encoded_video(self):
        self.inspector.inspect.side_effect = MediaInspectionError("source missing")
        self.assertIsNone(self.prepare())
        self.choose.assert_not_called()
        self.report.assert_called_once()
        self.assert_originals_unchanged()

    def test_vm_is_possible_without_full_subtitles(self):
        self.inspector.inspect.return_value["inspection"]["subtitle_tracks"] = []
        result = self.prepare(mode="original_without_subtitles")
        self.assertEqual("original_without_subtitles", result.session.track_selection["mode"])
        self.assert_originals_unchanged()

    def test_new_destination_avoids_a_previous_reencoding(self):
        first = suggested_output(self.project, "original_with_subtitles")
        first.write_bytes(b"previous reencoding")
        second = suggested_output(self.project, "original_with_subtitles")
        self.assertNotEqual(first, second)
        self.assertIn("VMST 2", second.stem)

    def test_exclusive_writer_preserves_a_file_created_during_identification(self):
        destination = self.root / "race.json"
        link = Mock()
        def identify(_document, target):
            target.write_text("concurrent project")
            return {"status": "disabled"}
        link.identify.side_effect = identify
        writer = TrimProjectFileWriter(self.writer.bridge, vidb_link=link)
        with self.assertRaises(FileExistsError):
            writer.save(self.session, destination, exclusive=True)
        self.assertEqual("concurrent project", destination.read_text())
        self.assert_originals_unchanged()


if __name__ == "__main__":
    unittest.main()
