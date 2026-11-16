from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import montage_condition_dialog as ui
from video_encoder_ui.montage_condition import declaration
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession


class MontageConditionDialogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.session = TrimSession()
        self.session.add_source(SourceReference("one", Path("/commun/émission.m2t")))
        self.session.add_segment(SegmentSelection("one", 1, 100))

    def test_widget_defaults_and_independent_damage(self):
        dialog = ui.MontageConditionDialog(None, self.session)
        self.addCleanup(dialog.close)
        self.assertEqual("complete", dialog.condition()["integrality"])
        dialog.damage.setCurrentIndex(dialog.damage.findData("severe"))
        dialog.integrality.setCurrentIndex(dialog.integrality.findData("beginning"))
        dialog.source.setCurrentIndex(1)
        value = dialog.condition()
        self.assertEqual("incomplete", value["integrality"])
        self.assertEqual("beginning", value["retained_portion"])
        self.assertEqual("severe", value["damage"])
        self.assertEqual(["/commun/émission.m2t"], value["affected_source_paths"])

    def test_cancelling_preserves_the_previous_declaration(self):
        self.session.copy_condition = declaration(self.session, damage="light")
        previous = self.session.copy_condition
        parent = SimpleNamespace(set_project_modified=Mock())
        with patch.object(ui, "MontageConditionDialog") as factory:
            factory.return_value.exec.return_value = QtWidgets.QDialog.DialogCode.Rejected
            self.assertFalse(ui.review_montage_condition(parent, self.session, force=True))
        self.assertIs(previous, self.session.copy_condition)
        parent.set_project_modified.assert_not_called()

    def test_acceptance_marks_the_project_modified_and_does_not_reprompt(self):
        parent = SimpleNamespace(set_project_modified=Mock())
        value = declaration(self.session, integrality="incomplete")
        with patch.object(ui, "MontageConditionDialog") as factory:
            factory.return_value.exec.return_value = QtWidgets.QDialog.DialogCode.Accepted
            factory.return_value.condition.return_value = value
            self.assertTrue(ui.review_montage_condition(parent, self.session))
            self.assertTrue(ui.review_montage_condition(parent, self.session))
            factory.assert_called_once()
        self.assertEqual(value, self.session.copy_condition)
        parent.set_project_modified.assert_called_once_with(True)
