import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    raise unittest.SkipTest("PySide6 is unavailable")

from video_encoder_ui import vidb_export_review as review


class VidbReviewModalWaitTest(unittest.TestCase):
    def test_early_modal_return_waits_for_the_actual_confirmation(self):
        dialog = Mock(closed=False, result_data={"status": "identified", "record_id": 123})
        dialog.exec.return_value = QtWidgets.QDialog.DialogCode.Rejected
        dialog.result.return_value = QtWidgets.QDialog.DialogCode.Accepted
        loop = Mock()

        def finish():
            dialog.closed = True

        loop.exec.side_effect = finish
        with patch.object(review, "VidbExportReview", return_value=dialog), \
             patch.object(review.QtCore, "QEventLoop", return_value=loop):
            result = review.await_vidb_identification(None, {}, Mock())
        self.assertEqual(123, result["record_id"])
        loop.exec.assert_called_once()
        dialog.finished.disconnect.assert_called_once_with(loop.quit)

    def test_an_actual_cancellation_does_not_restart_the_wait(self):
        dialog = Mock(closed=True)
        dialog.exec.return_value = QtWidgets.QDialog.DialogCode.Rejected
        with patch.object(review, "VidbExportReview", return_value=dialog), \
             patch.object(review.QtCore, "QEventLoop") as loop:
            self.assertIsNone(review.await_vidb_identification(None, {}, Mock()))
        loop.assert_not_called()
