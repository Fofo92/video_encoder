import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from video_encoder_ui.ad_analysis_workspace import AdAnalysisWorkspace
from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession


class AdAnalysisWorkspaceCleanupTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.source = self.directory / "capture.m2t"
        self.source.write_bytes(b"capture to preserve")
        fingerprint = hashlib.sha256(str(self.source.resolve()).encode()).hexdigest()[:12]
        self.root = self.directory / f"ad-analysis-{fingerprint}"
        (self.root / "boundaries").mkdir(parents=True)
        (self.root / "detection").mkdir()
        (self.root / "detection" / "frames.gray").write_bytes(b"intermediate")
        self.report = self.root / "boundaries" / "boundary-hypotheses.json"
        self.report.write_text(json.dumps({
            "format": "video_encoder.6ter_boundary_hypotheses", "version": 3, "source": str(self.source),
        }))
        self.document = {
            "format": "video_encoder.trim_project", "version": 2,
            "sources": [{"id": "source", "path": str(self.source)}],
            "timeline": [{"type": "segment", "source_id": "source", "start_frame": 100, "end_frame": 200}],
        }
        (self.root / "proposal.json").write_text(json.dumps(self.document))
        self.workspace = AdAnalysisWorkspace.for_report(self.report, self.source)
        self.assertIsNotNone(self.workspace)
        self.addCleanup(self.workspace.close)
        self.session = TrimSession()
        self.session.add_source(SourceReference("source", self.source))
        self.session.add_segment(SegmentSelection("source", 100, 200))
        self.session.analysis_workspaces.append(self.workspace)
        self.bridge = Mock()
        self.bridge.convert.return_value = self.document
        self.writer = TrimProjectFileWriter(self.bridge)
        self.destination = self.directory / "S04 E05 - Suis ta route.json"

    def test_saving_removes_intermediates_before_encoding_and_reopens_the_saved_montage(self):
        self.writer.save(self.session, self.destination)
        self.assertFalse(self.root.exists())
        self.assertFalse(self.destination.with_suffix(".mkv").exists())
        self.assertEqual(self.source.read_bytes(), b"capture to preserve")
        loaded = TrimProjectFileReader().load(self.destination)
        self.assertEqual(loaded.segments, self.session.segments)
        self.assertEqual(loaded.sources[0].path, self.source)
        loaded.replace_segment(0, SegmentSelection("source", 101, 199))
        self.assertEqual(loaded.segments[0].start_frame, 101)
        self.assertEqual(self.writer.cleanup_warnings, [])
        self.assertEqual(self.session.analysis_workspaces, [])

    def test_failed_project_conversion_does_not_remove_analysis(self):
        self.bridge.convert.side_effect = ValueError("invalid montage")
        with self.assertRaises(ValueError):
            self.writer.save(self.session, self.destination)
        self.assertTrue(self.root.exists())
        self.assertFalse(self.destination.exists())

    def test_abandoning_an_unsaved_proposal_keeps_its_analysis(self):
        self.workspace.close()
        self.assertTrue(self.report.exists())
        self.assertFalse(self.destination.exists())

    def test_atomic_save_preserves_existing_project_permissions(self):
        self.destination.write_text("old project")
        self.destination.chmod(0o640)
        self.writer.save(self.session, self.destination)
        self.assertEqual(self.destination.stat().st_mode & 0o777, 0o640)

    def test_failed_atomic_replacement_preserves_the_old_project_and_the_analysis(self):
        self.destination.write_text("old project")
        with patch("video_encoder_ui.trim_project_file_writer.os.replace", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.writer.save(self.session, self.destination)
        self.assertEqual(self.destination.read_text(), "old project")
        self.assertTrue(self.root.exists())
        self.assertEqual(list(self.directory.glob(".S04*.json.*")), [])

    def test_failed_disk_sync_does_not_remove_analysis(self):
        with patch("video_encoder_ui.trim_project_file_writer.os.fsync", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.writer.save(self.session, self.destination)
        self.assertTrue(self.root.exists())

    def test_cleanup_failure_keeps_a_successfully_saved_project_and_is_reported_separately(self):
        with patch("video_encoder_ui.ad_analysis_workspace.shutil.rmtree", side_effect=PermissionError("denied")):
            self.assertEqual(self.writer.save(self.session, self.destination), self.destination)
        saved = json.loads(self.destination.read_text())
        self.assertIn("project_id", saved)
        self.assertEqual({key: value for key, value in saved.items() if key != "project_id"}, self.document)
        self.assertTrue(self.root.exists())
        self.assertIn("denied", self.writer.cleanup_warnings[0])
        self.writer.save(self.session, self.destination)
        self.assertFalse(self.root.exists())

    def test_does_not_remove_a_project_saved_inside_the_analysis_directory(self):
        destination = self.root / "saved.json"
        self.writer.save(self.session, destination)
        self.assertTrue(destination.exists())
        self.assertTrue(self.root.exists())
        self.assertTrue(self.writer.cleanup_warnings)

    def test_another_open_preparation_keeps_the_analysis_until_it_has_also_been_saved(self):
        other = AdAnalysisWorkspace.for_report(self.report, self.source)
        self.addCleanup(other.close)
        self.writer.save(self.session, self.destination)
        self.assertTrue(self.root.exists())
        self.assertTrue(self.writer.cleanup_warnings)
        other.clean_after_save(self.destination, self.session.sources)
        self.assertFalse(self.root.exists())

    def test_refuses_unknown_contents_or_a_replaced_directory(self):
        (self.root / "personal.txt").write_text("keep")
        self.writer.save(self.session, self.destination)
        self.assertEqual((self.root / "personal.txt").read_text(), "keep")
        self.assertTrue(self.writer.cleanup_warnings)
        self.root.rename(self.directory / "original-analysis")
        self.root.mkdir()
        (self.root / "personal.txt").write_text("replacement")
        self.writer.save(self.session, self.destination)
        self.assertEqual((self.root / "personal.txt").read_text(), "replacement")
        self.assertIn("remplacé", self.writer.cleanup_warnings[0])

    def test_does_not_register_an_unrelated_report_or_a_symlink(self):
        self.assertIsNone(AdAnalysisWorkspace.for_report(self.report, self.directory / "other.m2t"))
        self.report.unlink()
        self.report.symlink_to(self.root / "proposal.json")
        self.assertIsNone(AdAnalysisWorkspace.for_report(self.report, self.source))


if __name__ == "__main__":
    unittest.main()
