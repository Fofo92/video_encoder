"""Exercise the ordinary editor, saved project and queue action together."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7
    from PySide6 import QtGui, QtWidgets
    from video_encoder_ui.application import MltFrameMonitor
except ModuleNotFoundError:
    QtWidgets = None

from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter


@unittest.skipIf(QtWidgets is None, "Qt or MLT unavailable")
class ManualEditorWorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_mark_save_reopen_and_request_queue_without_detector(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "capture.m2t"
            source.write_bytes(b"test source")
            image = QtGui.QImage(32, 18, QtGui.QImage.Format.Format_RGB32)
            image.fill(0)
            frames = SimpleNamespace(length=1000, frames_per_second=25,
                                     frame_at=lambda n: (image, n, 0), close=Mock())
            with patch("video_encoder_ui.application.MltFrameSource", return_value=frames), \
                 patch("video_encoder_ui.application.MltAudioPlayer"), \
                 patch("video_encoder_ui.application.ShuttleXpressReader", side_effect=OSError):
                editor = MltFrameMonitor(source)
            try:
                labels = [button.text() for button in editor.findChildren(QtWidgets.QPushButton)]
                self.assertNotIn("Analyser les publicités…", labels)
                self.assertNotIn("Créer avec coupures…", labels)
                self.assertFalse(hasattr(editor, "ad_analysis_runner"))
                self.assertFalse(hasattr(editor, "repeated_sequence_action"))
                for first, last in [(10, 200), (300, 800)]:
                    editor.show_frame(first)
                    editor.set_in_marker()
                    editor.show_frame(last)
                    editor.set_out_marker()
                    editor.add_segment_button.click()
                expected = [(10, 200), (300, 800)]
                self.assertEqual([(s.start_frame, s.end_frame) for s in editor.trim_session.segments], expected)
                document = {
                    "format": "video_encoder.trim_project", "version": 2,
                    "sources": [{"id": "source", "path": str(source)}],
                    "timeline": [{"type": "segment", "source_id": "source",
                                  "start_frame": a, "end_frame": b} for a, b in expected],
                }
                editor.trim_project_writer = TrimProjectFileWriter(Mock(convert=Mock(return_value=document)))
                destination = Path(directory) / "capture.json"
                self.assertEqual(editor.write_project(destination), destination)
                reopened = TrimProjectFileReader().load(destination)
                self.assertEqual([(s.start_frame, s.end_frame) for s in reopened.segments], expected)
                with patch.object(editor, "export_project") as enqueue:
                    editor.queue_export_action.trigger()
                enqueue.assert_called_once_with(queued=True)
                self.assertEqual(source.read_bytes(), b"test source")
            finally:
                editor.shutdown()
                editor.deleteLater()
