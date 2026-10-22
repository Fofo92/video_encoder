import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtCore
    from video_encoder_ui.application import MltFrameMonitor
    from video_encoder_ui.ad_analysis_workspace import AdAnalysisWorkspace
except ModuleNotFoundError:
    MltFrameMonitor = None

from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter
from video_encoder_ui.trim_session import SourceReference, TrimSession


@unittest.skipIf(MltFrameMonitor is None, "PySide6 or MLT is unavailable")
class ApplicationAnalysisCleanupTest(unittest.TestCase):
    def test_loading_editing_and_saving_a_managed_proposal_removes_only_its_intermediates(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            source = directory / "capture.m2t"
            source.write_bytes(b"capture")
            fingerprint = hashlib.sha256(str(source.resolve()).encode()).hexdigest()[:12]
            workspace = directory / f"ad-analysis-{fingerprint}"
            (workspace / "boundaries").mkdir(parents=True)
            report = workspace / "boundaries" / "boundary-hypotheses.json"
            report.write_text(json.dumps({
                "format": "video_encoder.6ter_boundary_hypotheses", "version": 3, "source": str(source),
            }))
            document = {
                "format": "video_encoder.trim_project", "version": 2,
                "sources": [{"id": "source", "path": str(source)}],
                "timeline": [{"type": "segment", "source_id": "source", "start_frame": 10, "end_frame": 80}],
            }
            (workspace / "proposal.json").write_text(json.dumps(document))
            # Old proposal JSON remains an ordinary editable project. Keep only
            # the compatibility helper that owns these known intermediates.
            session = TrimProjectFileReader().load(workspace / "proposal.json")
            session.analysis_workspaces.append(AdAnalysisWorkspace.for_report(report, source))
            original = session.segments[0]
            session.replace_segment(0, type(original)("source", 11, 79))
            self.assertTrue(workspace.exists())
            self.assertEqual(len(session.analysis_workspaces), 1)

            document["timeline"][0].update(source_id="source", start_frame=11, end_frame=79)
            writer = TrimProjectFileWriter(Mock(convert=Mock(return_value=document)))
            project = directory / "episode.json"
            writer.save(session, project)
            self.assertFalse(workspace.exists())
            self.assertTrue(source.exists())
            self.assertEqual(TrimProjectFileReader().load(project).segments, session.segments)

    def test_a_cleanup_warning_does_not_report_the_project_save_as_failed(self):
        monitor = SimpleNamespace(
            trim_session=TrimSession(),
            trim_project_writer=Mock(cleanup_warnings=["Nettoyage impossible"]),
            set_project_modified=Mock(), statusBar=Mock(return_value=Mock()),
        )
        monitor.trim_project_writer.save.return_value = Path("/saved.json")
        with patch("video_encoder_ui.application.QtWidgets.QMessageBox.warning") as warning:
            result = MltFrameMonitor.write_project(monitor, "/saved.json")
        self.assertEqual(result, Path("/saved.json"))
        self.assertEqual(monitor.project_path, Path("/saved.json"))
        self.assertIn("Projet enregistré", warning.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
