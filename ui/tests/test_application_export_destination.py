import json
import tempfile
import unittest
from pathlib import Path
from types import MethodType, SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7
    from video_encoder_ui.application import MltFrameMonitor
except ModuleNotFoundError:
    MltFrameMonitor = None


@unittest.skipIf(MltFrameMonitor is None, "PySide6 or MLT is unavailable")
class ApplicationExportDestinationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.segments = [{"start_frame": 100, "end_frame": 200}]
        self.monitor = SimpleNamespace(
            source_path=self.root / "capture.m2t", project_path=None,
            trim_session=SimpleNamespace(segments=self.segments),
            trim_project_exporter=Mock(is_running=False),
            audio_preflight_runner=Mock(is_running=False), pending_export=None,
            export_status_changed=Mock(), trim_export_queue_client=Mock(),
            trim_project_archiver=Mock(), audio_preflight_cancel_prompt_active=False,
            confirm_audio_preflight=Mock(return_value=False),
        )

        def write_project(path):
            path.write_text(json.dumps({"timeline": self.segments}))
            self.monitor.project_path = path
            return path

        self.monitor.write_project = Mock(side_effect=write_project)
        self.monitor.select_output_path = MethodType(MltFrameMonitor.select_output_path, self.monitor)

    def export_to(self, output, queued=True):
        with patch("video_encoder_ui.project_destination.choose_project_output",
                   return_value=(str(output), "")) as dialog:
            MltFrameMonitor.export_project(self.monitor, queued=queued)
        dialog.assert_called_once()

    def test_first_queue_choice_creates_the_matching_project_without_a_second_dialog(self):
        output = self.root / "S04 E05 - Suis ta route.mkv"
        self.export_to(output)
        self.assertEqual(self.monitor.pending_export, (output.with_suffix(".json"), output))
        saved = json.loads(output.with_suffix(".json").read_text())
        self.assertEqual(saved["timeline"], self.segments)
        self.monitor.audio_preflight_runner.start.assert_called_once_with(output.with_suffix(".json"))
        self.monitor.trim_export_queue_client.enqueue.assert_not_called()

    def test_cancelled_confirmation_allows_a_different_name_and_folder_without_enqueuing(self):
        first = self.root / "wrong.mkv"
        self.export_to(first)
        MltFrameMonitor.audio_preflight_succeeded(self.monitor, {"audio_checks": []})
        self.assertIsNone(self.monitor.pending_export)
        self.monitor.trim_export_queue_client.enqueue.assert_not_called()
        self.monitor.trim_project_archiver.archive.assert_not_called()
        self.monitor.trim_project_exporter.start.assert_not_called()

        folder = self.root / "Saison 04"
        folder.mkdir()
        second = folder / "S04 E05 - Suis ta route.mkv"
        self.export_to(second)
        self.assertEqual(self.monitor.pending_export, (second.with_suffix(".json"), second))
        self.assertEqual(json.loads(second.with_suffix(".json").read_text())["timeline"], self.segments)
        self.assertIs(self.monitor.trim_session.segments, self.segments)

    def test_immediate_export_uses_the_same_single_destination_choice(self):
        output = self.root / "movie.mkv"
        self.export_to(output, queued=False)
        self.assertEqual(self.monitor.pending_export_mode, "immediate")
        self.assertEqual(self.monitor.pending_export, (output.with_suffix(".json"), output))

    def test_successful_preflight_sets_one_status_argument(self):
        self.monitor.close_after_preflight = False
        self.monitor.pending_export = (self.root / "movie.json", self.root / "movie.mkv")
        MltFrameMonitor.audio_preflight_status_changed(self.monitor, "succeeded")
        self.monitor.export_status_changed.assert_called_once_with("confirming")

    def test_export_creates_the_project_in_the_new_nested_destination(self):
        output = self.root / 'Séries TV/Esprits criminels/Saison 07/S07 E01 - Tous pour elle.mkv'
        self.export_to(output)
        self.assertTrue(output.with_suffix('.json').is_file())
        self.assertEqual((output.with_suffix('.json'), output), self.monitor.pending_export)


if __name__ == "__main__":
    unittest.main()
