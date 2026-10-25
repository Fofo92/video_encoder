import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from PySide6 import QtGui, QtWidgets
    import mlt7
except ModuleNotFoundError as error:
    if error.name not in {"PySide6", "mlt7"}:
        raise
    raise unittest.SkipTest("PySide6 or MLT is unavailable") from error

from video_encoder_ui.application import MltFrameMonitor
from video_encoder_ui.trim_session import TrimSession, SourceReference, SegmentSelection


class Preview:
    def __init__(self, path, preview_width=640, preview_height=360):
        self.path = Path(path)
        self.preview_width, self.preview_height = preview_width, preview_height
        self.frame_rate_numerator, self.frame_rate_denominator = 25, 1
        self.frames_per_second, self.length = 25, 10000
        self.close = Mock()

    def frame_at(self, position):
        return QtGui.QImage(self.preview_width, self.preview_height, QtGui.QImage.Format.Format_RGBA8888), position, 0


class MultiSourceEditorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.a, self.b = root / "premiere.m2t", root / "seconde.m2t"
        self.a.touch()
        self.b.touch()
        self.session = TrimSession()
        self.session.add_source(SourceReference("A", self.a))
        self.session.add_source(SourceReference("B", self.b))
        self.session.add_segment(SegmentSelection("A", 100, 200))
        self.session.add_segment(SegmentSelection("B", 300, 400))
        self.session.add_segment(SegmentSelection("A", 500, 600))
        self.preview_patch = patch("video_encoder_ui.application.MltFrameSource", Preview)
        self.other_preview_patch = patch("video_encoder_ui.multi_source_editor.MltFrameSource", Preview)
        def audio(_path):
            player = Mock(is_playing=False)
            player.stop.return_value = None
            return player
        self.audio_patch = patch("video_encoder_ui.application.MltAudioPlayer", side_effect=audio)
        self.other_audio_patch = patch("video_encoder_ui.multi_source_editor.MltAudioPlayer", side_effect=audio)
        self.shuttle_patch = patch("video_encoder_ui.application.ShuttleXpressReader", side_effect=OSError("No device"))
        for item in (self.preview_patch, self.other_preview_patch, self.audio_patch, self.other_audio_patch, self.shuttle_patch):
            item.start()
            self.addCleanup(item.stop)
        self.window = MltFrameMonitor(self.a, trim_session=self.session)
        self.addCleanup(self.close_window)

    def close_window(self):
        self.window.project_modified = False
        self.window.close()
        self.window.deleteLater()

    def test_source_switch_preserves_timeline_and_restores_position(self):
        self.window.show_frame(700)
        original = self.session.segments
        self.assertTrue(self.window.activate_source("B"))
        self.assertEqual(self.window.source_path, self.b)
        self.assertEqual(self.window.current_position, 0)
        self.assertEqual(self.session.segments, original)
        self.assertTrue(self.window.activate_source("A"))
        self.assertEqual(self.window.current_position, 700)
        self.assertEqual(self.window.segment_list.item(1, 1).text(), self.b.name)

    def test_selecting_another_source_segment_opens_that_source_and_can_edit_it(self):
        self.window.segment_list.selectRow(1)
        self.window.select_segment(1)
        self.assertEqual(self.window.source_id, "B")
        self.assertEqual(self.window.current_position, 300)
        self.assertEqual(self.window.segment_list.currentRow(), 1)
        self.window.edit_selected_segment()
        self.assertEqual(self.window.editing_segment_index, 1)
        self.assertEqual((self.window.in_position, self.window.out_position), (300, 400))

    def test_source_switch_can_be_cancelled_without_losing_markers(self):
        self.window.in_position = 100
        with patch("video_encoder_ui.multi_source_editor.QtWidgets.QMessageBox.question",
                   return_value=QtWidgets.QMessageBox.StandardButton.No):
            self.assertFalse(self.window.activate_source("B"))
        self.assertEqual(self.window.source_id, "A")
        self.assertEqual(self.window.in_position, 100)

    def test_busy_export_blocks_source_changes_and_reordering(self):
        original = self.session.segments
        self.window.export_status_changed("preflight")
        self.assertFalse(self.window.source_selector.isEnabled())
        self.assertFalse(self.window.activate_source("B"))
        self.window.move_selected_segment(1)
        self.assertEqual(self.session.segments, original)
        self.window.export_status_changed("idle")

    def test_reordering_preserves_source_and_frame_bounds(self):
        self.window.segment_list.selectRow(1)
        self.window.move_selected_segment(1)
        self.assertEqual([s.source_id for s in self.session.segments], ["A", "A", "B"])
        self.assertEqual(self.session.segments[2], SegmentSelection("B", 300, 400))
        self.assertTrue(self.window.project_modified)

    def test_wrong_cadence_is_rejected_without_changing_active_source(self):
        preview = Preview(self.b)
        preview.frame_rate_numerator = 30
        with patch.object(self.window, "open_source_preview", return_value=preview), \
             patch("video_encoder_ui.multi_source_editor.QtWidgets.QMessageBox.warning") as warning:
            self.assertFalse(self.window.activate_source("B"))
        self.assertEqual(self.window.source_id, "A")
        preview.close.assert_called_once()
        warning.assert_called_once()

    def test_duplicate_source_is_selected_without_adding_a_reference(self):
        with patch("video_encoder_ui.multi_source_editor.QtWidgets.QFileDialog.getOpenFileName",
                   return_value=(str(self.b), "")):
            self.window.add_montage_source()
        self.assertEqual(len(self.session.sources), 2)
        self.assertEqual(self.window.source_id, "B")

    def test_adds_a_third_source_and_saves_its_identity_in_the_session(self):
        third = self.a.parent / "troisieme.m2t"
        third.touch()
        with patch("video_encoder_ui.multi_source_editor.QtWidgets.QFileDialog.getOpenFileName",
                   return_value=(str(third), "")):
            self.window.add_montage_source()
        self.assertEqual(len(self.session.sources), 3)
        self.assertEqual(self.window.source_path, third)
        self.assertEqual(self.session.to_document()["sources"][2]["path"], str(third))

    def test_saved_multi_source_project_reopens_without_changing_order_or_bounds(self):
        import json
        from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
        from video_encoder_ui.application import load_startup_selection
        document = self.session.to_document()
        document.update(format="video_encoder.trim_project", version=2)
        for item in document["timeline"]:
            item["type"] = "segment"
        path = self.a.parent / "montage.json"
        path.write_text(json.dumps(document))
        first, restored, _project = load_startup_selection(path, reader=TrimProjectFileReader())
        self.assertEqual(first, self.a)
        self.assertEqual(restored.sources, self.session.sources)
        self.assertEqual(restored.segments, self.session.segments)

    def test_missing_source_does_not_destroy_the_active_preview(self):
        self.b.unlink()
        original = self.window.frame_source
        with patch("video_encoder_ui.multi_source_editor.QtWidgets.QMessageBox.warning"):
            self.assertFalse(self.window.activate_source("B"))
        self.assertIs(self.window.frame_source, original)
        original.close.assert_not_called()

    def test_reopening_rejects_an_incompatible_source_before_editing(self):
        wrong = Preview(self.b)
        wrong.frame_rate_numerator = 30
        with patch.object(self.window, "open_source_preview", return_value=wrong):
            with self.assertRaises(ValueError):
                self.window.validate_source_cadences()
        wrong.close.assert_called_once()


class MultiSourceOrderTest(unittest.TestCase):
    def test_invalid_reordering_leaves_the_existing_timeline_unchanged(self):
        session = TrimSession()
        session.add_source(SourceReference("A", Path("a.m2t")))
        session.add_segment(SegmentSelection("A", 100, 200))
        session.add_segment(SegmentSelection("A", 400, 500))
        original = session.segments
        with self.assertRaises(ValueError):
            session.move_segment(0, 1)
        self.assertEqual(session.segments, original)
