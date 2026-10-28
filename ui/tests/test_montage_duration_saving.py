import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7
    from video_encoder_ui.application import MltFrameMonitor
except ModuleNotFoundError:
    MltFrameMonitor = None


@unittest.skipIf(MltFrameMonitor is None, "PySide6 or MLT is unavailable")
class MontageDurationSavingTest(unittest.TestCase):
    def test_return_to_montage_never_calls_the_project_writer(self):
        monitor = SimpleNamespace(trim_project_writer=Mock(), set_project_modified=Mock(), statusBar=Mock())
        with patch("video_encoder_ui.montage_duration.confirm_montage_duration", return_value=False):
            self.assertIsNone(MltFrameMonitor.write_project(monitor, Path("/videos/test.json")))
        monitor.trim_project_writer.save.assert_not_called()
        monitor.set_project_modified.assert_not_called()
        monitor.statusBar.assert_not_called()

    def test_approved_check_preserves_the_normal_save_path(self):
        destination = Path("/videos/test.json")
        writer = Mock(vidb_result={"status": "disabled"}, cleanup_warnings=[])
        writer.save.return_value = destination
        monitor = SimpleNamespace(trim_project_writer=writer, trim_session=object(),
                                  set_project_modified=Mock(), statusBar=Mock())
        with patch("video_encoder_ui.montage_duration.confirm_montage_duration", return_value=True):
            self.assertEqual(destination, MltFrameMonitor.write_project(monitor, destination))
        writer.save.assert_called_once_with(monitor.trim_session, destination)
        self.assertEqual(destination, monitor.project_path)
