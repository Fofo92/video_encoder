from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

try:
    import mlt7
    from video_encoder_ui.application import MltFrameMonitor
except ModuleNotFoundError:
    MltFrameMonitor = None


@unittest.skipIf(MltFrameMonitor is None, "PySide6 or MLT is unavailable")
class ReencodeProjectUiTest(unittest.TestCase):
    def setUp(self):
        self.old_session = object()
        self.prepared = SimpleNamespace(session=object(), project_path=Path('/videos/new.json'),
                                        output_path=Path('/videos/new.mkv'))
        self.monitor = SimpleNamespace(trim_session=self.old_session, project_path=Path('/videos/old.json'),
                                       trim_project_exporter=Mock(is_running=False),
                                       audio_preflight_runner=Mock(is_running=False), pending_export=None,
                                       pending_export_mode=None, trim_project_writer=Mock(),
                                       set_project_modified=Mock(), export_status_changed=Mock())

    def test_reencoding_starts_preflight_with_the_new_project_without_regular_destination_identification(self):
        with patch('video_encoder_ui.reencode_project.prepare_reencode', return_value=self.prepared), \
                patch('video_encoder_ui.application.offer_vidb_review', return_value=True):
            MltFrameMonitor.reencode_project(self.monitor)
        self.assertIs(self.prepared.session, self.monitor.trim_session)
        self.assertEqual((self.prepared.project_path, self.prepared.output_path), self.monitor.pending_export)
        self.assertEqual('queued', self.monitor.pending_export_mode)
        self.monitor.audio_preflight_runner.start.assert_called_once_with(self.prepared.project_path)
        self.monitor.trim_project_exporter.start.assert_not_called()

    def test_cancellation_or_an_active_export_does_not_start_preflight(self):
        with patch('video_encoder_ui.reencode_project.prepare_reencode', return_value=None) as prepare:
            MltFrameMonitor.reencode_project(self.monitor)
            prepare.assert_called_once()
            prepare.reset_mock()
            self.monitor.trim_project_exporter.is_running = True
            MltFrameMonitor.reencode_project(self.monitor)
            prepare.assert_not_called()
        self.assertIs(self.old_session, self.monitor.trim_session)
        self.monitor.audio_preflight_runner.start.assert_not_called()

    def test_unresolved_vidb_review_can_still_cancel_the_export(self):
        with patch('video_encoder_ui.reencode_project.prepare_reencode', return_value=self.prepared), \
                patch('video_encoder_ui.application.offer_vidb_review', return_value=False):
            MltFrameMonitor.reencode_project(self.monitor)
        self.monitor.audio_preflight_runner.start.assert_not_called()
        self.assertIsNone(self.monitor.pending_export)

    def test_failed_preflight_start_clears_the_pending_export(self):
        self.monitor.audio_preflight_runner.start.side_effect = RuntimeError('unavailable')
        with patch('video_encoder_ui.reencode_project.prepare_reencode', return_value=self.prepared), \
                patch('video_encoder_ui.application.offer_vidb_review', return_value=True), \
                patch('video_encoder_ui.application.QtWidgets.QMessageBox.warning') as warning:
            MltFrameMonitor.reencode_project(self.monitor)
        self.assertIsNone(self.monitor.pending_export)
        self.assertIsNone(self.monitor.pending_export_mode)
        self.monitor.export_status_changed.assert_called_once_with('failed')
        warning.assert_called_once()


if __name__ == '__main__':
    unittest.main()
