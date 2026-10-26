from concurrent.futures import Future
import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtCore, QtWidgets
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import vidb_export_review as review


class VidbExportReviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.pool, self.future = Mock(), Future()
        self.pool.submit.return_value = self.future
        for item in [patch.object(review, "ThreadPoolExecutor", return_value=self.pool),
                     patch.object(review, "build_vidb_browser", side_effect=lambda parent, url: QtWidgets.QLabel("vidb", parent))]:
            value = item.start()
            self.addCleanup(item.stop)
            self.opened = value
        self.result = {"status": "unmatched", "review_url": "https://vidb.test/encoder_projects/catalogue"}

    def dialog(self, result=None):
        dialog = review.VidbExportReview(None, result or self.result, Mock())
        dialog.timer.stop()
        self.addCleanup(dialog.deleteLater)
        self.addCleanup(dialog.reject)
        return dialog

    def test_validation_resumes_the_export_after_automatic_browser_opening(self):
        dialog = self.dialog()
        self.app.processEvents()
        self.opened.assert_called_once()
        dialog.poll()
        identified = {"status": "identified", "record_id": 123}
        dialog.preparation_completed(123)
        self.future.set_result(identified)
        dialog.poll()
        self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)
        self.assertEqual(dialog.result_data, identified)
        self.pool.shutdown.assert_called_once_with(wait=False, cancel_futures=True)

    def test_unresolved_identity_requires_explicit_continuation(self):
        dialog = self.dialog()
        dialog.poll()
        self.future.set_result(self.result)
        dialog.poll()
        self.assertFalse(dialog.closed)
        dialog.continue_button.click()
        self.assertTrue(dialog.closed)
        self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Accepted)

    def test_single_background_request_and_cancellation(self):
        dialog = self.dialog()
        for _ in range(5):
            dialog.poll()
        self.pool.submit.assert_called_once()
        dialog.reject()
        dialog.poll()
        self.assertTrue(dialog.closed)
        self.pool.submit.assert_called_once()
        self.assertEqual(dialog.result(), QtWidgets.QDialog.DialogCode.Rejected)

    def test_metadata_changes_alone_do_not_close_the_review(self):
        identified = {"status": "identified", "metadata": {"year": None}}
        dialog = self.dialog(identified)
        dialog.poll()
        self.future.set_result(identified)
        dialog.poll()
        self.assertFalse(dialog.closed)
        next_future = Future()
        next_future.set_result({**identified, "metadata": {"year": 2026}})
        self.pool.submit.return_value = next_future
        dialog.next_refresh = 0
        dialog.poll()
        dialog.poll()
        self.assertFalse(dialog.closed)
        self.assertEqual(dialog.result_data["metadata"]["year"], 2026)

    def test_offline_refresh_preserves_existing_identity(self):
        identified = {"status": "identified", "record_id": 123, "metadata": {"year": None}}
        dialog = self.dialog(identified)
        dialog.poll()
        self.future.set_result({"status": "pending"})
        dialog.poll()
        self.assertEqual(dialog.result_data, identified)
        self.assertFalse(dialog.closed)

    def test_network_failure_never_automatically_continues(self):
        dialog = self.dialog()
        dialog.poll()
        self.future.set_exception(OSError("offline"))
        dialog.poll()
        self.assertFalse(dialog.closed)
        self.assertIn("indisponible", dialog.status_label.text())

    def test_browser_runtime_error_is_reported_without_rejecting_the_montage(self):
        dialog = self.dialog()
        self.opened.side_effect = RuntimeError("internal request_token=private")
        dialog.open_review()
        self.assertIn("RuntimeError", dialog.status_label.text())
        self.assertNotIn("private", dialog.status_label.text())
        self.assertFalse(dialog.closed)

    def test_automatic_recognition_does_not_close_an_unreviewed_proposal(self):
        dialog = self.dialog()
        dialog.poll()
        self.future.set_result({"status": "identified", "record_id": 123})
        dialog.poll()
        self.assertFalse(dialog.closed)
        self.assertIn("fiche identifiée", dialog.continue_button.text())

    def test_confirmation_for_another_record_does_not_resume_encoding(self):
        dialog = self.dialog()
        dialog.preparation_completed(456)
        dialog.poll()
        self.future.set_result({"status": "identified", "record_id": 123})
        dialog.poll()
        self.assertFalse(dialog.closed)

    def test_confirming_unchanged_metadata_resumes_when_the_project_binding_matches(self):
        identified = {"status": "identified", "record_id": 123, "metadata": {"year": 2026}}
        dialog = self.dialog(identified)
        dialog.preparation_completed(123)
        dialog.poll()
        self.future.set_result(identified)
        dialog.poll()
        self.assertTrue(dialog.closed)

    def test_browser_form_redirect_then_matching_binding_resumes_the_export(self):
        class View(QtWidgets.QLabel):
            urlChanged = QtCore.Signal(QtCore.QUrl)

        self.opened.side_effect = lambda parent, _url: View("vidb", parent)
        dialog = self.dialog()
        self.app.processEvents()
        dialog.browser.urlChanged.emit(QtCore.QUrl("https://vidb.test/records/123?encoder_prepared=1"))
        self.assertEqual(123, dialog.confirmed_record_id)
        dialog.poll()
        self.future.set_result({"status": "identified", "record_id": 123})
        dialog.poll()
        self.assertTrue(dialog.closed)
