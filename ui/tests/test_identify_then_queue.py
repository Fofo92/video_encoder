import json
import tempfile
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
    import mlt7
except ModuleNotFoundError as error:
    if error.name not in {"PySide6", "mlt7"}:
        raise
    raise unittest.SkipTest("PySide6 or MLT is unavailable") from error

from video_encoder_ui import catalogue_destination as destination
from video_encoder_ui.application import MltFrameMonitor
from video_encoder_ui.vidb_project_link import VidbProjectLink


class IdentifyThenQueueTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        config = self.root / "vidb.json"
        config.write_text(json.dumps({"url": "https://vidb.test", "token": "a" * 64}))
        self.transport = Mock(return_value={"status": "unmatched", "review_url": "https://vidb.test/encoder_projects/catalogue"})
        self.writer = SimpleNamespace(vidb_link=VidbProjectLink(config, transport=self.transport))
        self.source = Path("/commun/to_be_cut/Documentaire.m2t")
        self.session = SimpleNamespace(sources=[SimpleNamespace(path=self.source)], segments=[object()])

    def test_browser_validation_continues_in_the_same_call(self):
        def refresh(_parent, result, callback):
            self.transport.return_value = {"status": "identified", "binding": {
                "project_id": self.session.project_id, "record_id": 123, "binding_token": "signed"},
                "metadata": {"record_kind": "standalone_video", "french_title": "Documentaire", "genres": ["Documentaire"]}}
            return callback()
        with patch.object(destination, "await_vidb_identification", side_effect=refresh), \
             patch.object(destination, "confirm_destination", return_value=Path("/videos/Documentaires/Documentaire.mkv")) as confirm:
            result = destination.prepare_catalogue_destination(None, self.session, self.source,
                Path("/videos/Documentaire.mkv"), self.writer, continue_export=True)
        self.assertEqual(result.parent, Path("/videos/Documentaires"))
        self.assertEqual(self.session.vidb["record_id"], 123)
        self.assertEqual(confirm.call_args.args[1]["genres"], ["Documentaire"])
        self.assertEqual(self.transport.call_count, 2)

    def test_cancel_preserves_montage_and_does_not_offer_a_destination(self):
        with patch.object(destination, "await_vidb_identification", return_value=None), \
             patch.object(destination, "confirm_destination") as confirm:
            result = destination.prepare_catalogue_destination(None, self.session, self.source,
                Path("/videos/Documentaire.mkv"), self.writer, continue_export=True)
        self.assertIsNone(result)
        confirm.assert_not_called()
        self.assertEqual(len(self.session.segments), 1)

    def test_explicit_continuation_reaches_audio_then_enqueues_once(self):
        project, output = self.root / "test.json", self.root / "test.mkv"
        monitor = SimpleNamespace(trim_session=self.session, trim_project_writer=self.writer,
            source_path=self.source, project_path=None, trim_project_exporter=Mock(is_running=False),
            audio_preflight_runner=Mock(is_running=False), pending_export=None, write_project=Mock(return_value=project),
            export_status_changed=Mock(), trim_export_queue_client=Mock(), trim_project_archiver=Mock(),
            audio_preflight_cancel_prompt_active=False, confirm_audio_preflight=Mock(return_value=True),
            statusBar=Mock(), new_montage=Mock())
        monitor.select_output_path = MethodType(MltFrameMonitor.select_output_path, monitor)
        monitor.trim_project_archiver.archive.return_value = project
        with patch.object(destination, "await_vidb_identification", return_value={"status": "unmatched"}), \
             patch("video_encoder_ui.application.select_project_output", return_value=output), \
             patch("video_encoder_ui.application.offer_vidb_review", side_effect=AssertionError("second menu")), \
             patch("video_encoder_ui.original_language_review.prepare_track_selection", return_value=True) as language_review:
            MltFrameMonitor.export_project(monitor, queued=True)
        language_review.assert_called_once_with(monitor, project)
        monitor.audio_preflight_runner.start.assert_called_once_with(project)
        self.assertEqual(monitor.pending_export_mode, "queued")
        new_button, current_button = object(), object()
        dialog = Mock()
        dialog.addButton.side_effect = [new_button, current_button, object()]
        dialog.clickedButton.return_value = new_button
        with patch("video_encoder_ui.application.QtWidgets.QMessageBox", return_value=dialog):
            MltFrameMonitor.audio_preflight_succeeded(monitor, {"audio_checks": []})
        monitor.trim_export_queue_client.enqueue.assert_called_once_with(project, output)
        monitor.new_montage.assert_called_once()
        MltFrameMonitor.audio_preflight_succeeded(monitor, {"audio_checks": []})
        monitor.trim_export_queue_client.enqueue.assert_called_once_with(project, output)

    def test_a_complete_identified_film_goes_directly_to_its_destination(self):
        def transport(_config, payload):
            return {"status": "identified", "binding": {"project_id": payload["project"]["project_id"],
                    "record_id": 123, "binding_token": "signed"},
                    "metadata": {"record_kind": "standalone_video", "french_title": "Documentaire",
                                 "genres": ["Documentaire"], "countries": ["France"],
                                 "year": 2026, "abstract": "Bref résumé"}}
        self.writer.vidb_link.transport = transport
        with patch.object(destination, "confirm_destination") as confirm, \
             patch.object(destination, "await_vidb_identification") as wait:
            result = destination.prepare_catalogue_destination(None, self.session, self.source,
                Path("/videos/Documentaire.mkv"), self.writer, continue_export=True)
        self.assertEqual(result, Path("/videos/Documentaires/Documentaire.mkv"))
        confirm.assert_not_called()
        wait.assert_not_called()
