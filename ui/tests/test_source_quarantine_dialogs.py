import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import source_quarantine_dialogs as dialogs


class SourceQuarantineDialogsTest(unittest.TestCase):
    def test_selection_returns_every_distinct_source_in_the_selected_order(self):
        paths = ["/commun/to_be_cut/Film 1.m2t", "/commun/to_be_cut/Film 2.m2t"]
        with patch.object(dialogs.QtWidgets.QFileDialog, "getOpenFileNames",
                          return_value=([*paths, paths[0]], "")) as select:
            result = dialogs.select_quarantine_sources()
        self.assertEqual([Path(path) for path in paths], result)
        self.assertIn("sources", select.call_args.args[1])

    def test_cancelled_selection_returns_no_source(self):
        with patch.object(dialogs.QtWidgets.QFileDialog, "getOpenFileNames", return_value=([], "")):
            self.assertIsNone(dialogs.select_quarantine_sources())

    def test_confirmation_lists_every_source_and_defaults_to_no(self):
        paths = [Path("/commun/one.m2t"), Path("/commun/two.m2t")]
        with patch.object(dialogs.QtWidgets, "QMessageBox") as box:
            box.return_value.exec.return_value = box.StandardButton.No
            self.assertFalse(dialogs.confirm_quarantine_sources(None, paths))
        box.return_value.setDefaultButton.assert_called_once_with(box.StandardButton.No)
        box.return_value.setDetailedText.assert_called_once_with("\n".join(map(str, paths)))
        self.assertIn("tous les programmes", box.return_value.setInformativeText.call_args.args[0])

    def test_report_contains_both_moved_and_preserved_paths_in_a_single_dialog(self):
        with patch.object(dialogs.QtWidgets, "QMessageBox") as box:
            dialogs.report_quarantine_batch(None, ["/commun/one.m2t"], [("/commun/two.m2t", "active_trim_exports")])
        box.return_value.exec.assert_called_once()
        self.assertIn("1 source(s) déplacée(s) ; 1 conservée(s)", box.return_value.setText.call_args.args[0])
        self.assertIn("active_trim_exports", box.return_value.setDetailedText.call_args.args[0])
