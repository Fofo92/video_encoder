from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui import copy_version_dialog as module


@unittest.skipIf(QtWidgets is None, "PySide6 unavailable")
class CopyVersionDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.parent = QtWidgets.QWidget()
        self.addCleanup(self.parent.close)
        self.addCleanup(self.parent.deleteLater)

    def test_no_audio_or_burned_subtitle_confirmation_is_implied_by_qaas_presence(self):
        details = {"streams": [
            {"index": 1, "codec_type": "audio", "tags": {"language": "fra"}},
            {"index": 2, "codec_type": "audio", "tags": {"language": "qaa"}}]}

        def inspect(dialog):
            tracks = dialog.findChild(QtWidgets.QComboBox)
            checks = dialog.findChildren(QtWidgets.QCheckBox)
            ok = dialog.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
            self.assertEqual(tracks.currentIndex(), -1)
            self.assertFalse(ok.isEnabled())
            tracks.setCurrentIndex(1)
            self.assertFalse(ok.isEnabled())
            checks[0].setChecked(True)
            self.assertFalse(ok.isEnabled())
            checks[1].setChecked(True)
            self.assertTrue(ok.isEnabled())
            return QtWidgets.QDialog.DialogCode.Accepted

        class ReviewedDialog(QtWidgets.QDialog):
            def exec(self):
                return inspect(self)

        with patch.object(QtWidgets, "QDialog", ReviewedDialog):
            self.assertEqual(module.choose_original(self.parent, Path("/videos/test.mkv"), details), 2)

    def test_cancelling_track_selection_neither_identifies_nor_queues_a_project(self):
        core = Mock()
        core.identity.return_value = {"unchanged": True}
        queue = Mock()
        with patch.object(module, "pipeline", return_value=core), \
             patch.object(module, "choose_original", return_value=None), \
             patch.object(module, "identify") as identify:
            self.assertFalse(module.prepare_copy_version(self.parent, queue, source="/videos/test.mkv"))
        queue.enqueue.assert_not_called()
        core.prepare.assert_not_called()
        identify.assert_not_called()

    def test_final_confirmation_adds_only_to_the_existing_queue_with_the_confirmed_binding(self):
        core = Mock()
        core.identity.return_value = {"unchanged": True}
        document = {"format": "video_encoder.copy_version", "version": 2, "project_id": "new",
                    "sources": [{"id": "copy", "path": "/videos/source.mkv"}], "version_change": {}}
        core.prepare.return_value = document
        context = {"project_id": "bound-id", "record_id": 42}
        binding = {"status": "identified", "record_id": 42}
        link = Mock()
        link.identify.return_value = binding
        queue = Mock()
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(module, "pipeline", return_value=core), \
             patch.object(module, "choose_original", return_value=2), \
             patch.object(module, "confirm_queue", return_value=True), \
             patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(folder + "/VOST.mkv", "")), \
             patch.object(QtWidgets.QMessageBox, "information"):
            self.assertTrue(module.prepare_copy_version(self.parent, queue, source="/videos/source.mkv",
                                                        context=context, ticket="signed", link=link))
            self.assertTrue(Path(folder, "VOST.json").exists())
        self.assertEqual(document["project_id"], "new")
        self.assertEqual(document["vidb"], binding)
        self.assertNotIn("vidb_launch", document)
        queue.enqueue.assert_called_once()
        queue.start.assert_not_called()

    def test_cancelled_queue_confirmation_does_not_contact_vidb(self):
        core = Mock()
        core.identity.return_value = {"unchanged": True}
        queue = Mock()
        with tempfile.TemporaryDirectory() as folder, \
             patch.object(module, "pipeline", return_value=core), \
             patch.object(module, "choose_original", return_value=2), \
             patch.object(module, "confirm_queue", return_value=False), \
             patch.object(module, "identify") as identify, \
             patch.object(QtWidgets.QFileDialog, "getSaveFileName", return_value=(folder + "/VOST.mkv", "")):
            self.assertFalse(module.prepare_copy_version(self.parent, queue, source="/videos/source.mkv"))
        identify.assert_not_called()
        queue.enqueue.assert_not_called()
