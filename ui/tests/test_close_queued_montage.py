import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest('PySide6 or MLT is unavailable')

from video_encoder_ui.application import MltFrameMonitor


class CloseQueuedMontageTest(unittest.TestCase):
    def test_close_keeps_the_queued_job_and_closes_only_the_editor(self):
        project, output = Path('/videos/test.json'), Path('/videos/test.mkv')
        monitor = SimpleNamespace(
            audio_preflight_cancel_prompt_active=False, pending_export=(project, output),
            pending_export_mode='queued', confirm_audio_preflight=Mock(return_value=True),
            trim_project_archiver=Mock(), trim_export_queue_client=Mock(),
            export_status_changed=Mock(), statusBar=Mock(), close=Mock(),
            new_montage=Mock())
        monitor.trim_project_archiver.archive.return_value = project
        buttons = [object(), object(), object()]
        dialog = Mock()
        dialog.addButton.side_effect = buttons
        dialog.clickedButton.return_value = buttons[2]
        with patch('video_encoder_ui.application.QtWidgets.QMessageBox', return_value=dialog):
            MltFrameMonitor.audio_preflight_succeeded(monitor, {'audio_checks': []})
        monitor.trim_export_queue_client.enqueue.assert_called_once_with(project, output)
        monitor.close.assert_called_once_with()
        monitor.new_montage.assert_not_called()
        self.assertIsNone(monitor.pending_export)
