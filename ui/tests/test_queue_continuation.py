import unittest
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui.trim_export_queue_controller import TrimExportQueueController
from video_encoder_ui.trim_export_queue_dialog import TrimExportQueueDialog


class QueueContinuationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def controller(self):
        runner = Mock(is_running=True, finish_current_requested=False)
        controller = TrimExportQueueController(Mock(), runner, Mock())
        controller.dialog = Mock()
        controller.refresh = Mock()
        return controller, runner, controller.dialog

    def test_request_during_single_job_does_not_start_a_second_worker(self):
        controller, runner, dialog = self.controller()
        controller.selected_job_id = "test"
        controller.start(dialog)
        self.assertTrue(controller.continue_after_current)
        runner.start.assert_not_called()
        dialog.set_continue_after_current_requested.assert_called_once_with(True)
        runner.is_running = False
        with patch("video_encoder_ui.trim_export_queue_controller.QtWidgets.QMessageBox.information") as info:
            controller.succeeded()
        runner.start.assert_called_once_with()
        self.assertFalse(controller.continue_after_current)
        self.assertIsNone(controller.selected_job_id)
        info.assert_not_called()

    def test_request_while_stopping_resumes_after_the_current_export(self):
        controller, runner, dialog = self.controller()
        runner.finish_current_requested = True
        controller.start(dialog)
        runner.start.assert_not_called()
        runner.is_running = False
        controller.stopped()
        runner.start.assert_called_once_with()
        dialog.set_single_job_running.assert_called_with(False)

    def test_interrupt_cancels_requested_continuation(self):
        controller, runner, _dialog = self.controller()
        controller.continue_after_current = True
        with patch("video_encoder_ui.trim_export_queue_controller.QtWidgets.QMessageBox.information"):
            controller.interrupted()
        runner.start.assert_not_called()
        self.assertFalse(controller.continue_after_current)

    def test_failure_continues_only_when_the_user_requested_it(self):
        controller, runner, _dialog = self.controller()
        controller.continue_after_current = True
        runner.is_running = False
        with patch("video_encoder_ui.trim_export_queue_controller.QtWidgets.QMessageBox.warning"):
            controller.failed("test failure")
        runner.start.assert_called_once_with()
        self.assertFalse(controller.continue_after_current)

    def test_normal_queue_does_not_schedule_a_duplicate_start(self):
        controller, runner, dialog = self.controller()
        controller.start(dialog)
        self.assertFalse(controller.continue_after_current)
        runner.start.assert_not_called()

    def test_button_exposes_continuation_without_allowing_repeated_requests(self):
        dialog = TrimExportQueueDialog([{"id": "test", "status": "running"}])
        self.addCleanup(dialog.deleteLater)
        dialog.set_running(True)
        dialog.set_single_job_running(True)
        self.assertTrue(dialog.start_button.isEnabled())
        self.assertIn("Enchaîner", dialog.start_button.text())
        dialog.set_continue_after_current_requested(True)
        self.assertFalse(dialog.start_button.isEnabled())
        self.assertEqual(dialog.start_button.text(), "Suite programmée")
        dialog.set_running(False)
        self.assertFalse(dialog.continue_after_current)
