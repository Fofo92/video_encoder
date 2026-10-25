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
from video_encoder_ui.trim_export_queue_runner import TrimExportQueueRunner


class RunSelectedQueueJobTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def jobs(self):
        return [{"id": name, "kind": "trim_export", "input_path": f"/tmp/{name}.json",
                 "output_path": f"/tmp/{name}.mkv", "status": "queued"} for name in ("first", "test", "last")]

    def test_dialog_emits_only_the_selected_job_and_leaves_job_order_unchanged(self):
        jobs = self.jobs()
        dialog = TrimExportQueueDialog(jobs)
        self.addCleanup(dialog.deleteLater)
        row = next(index for index, job in enumerate(dialog.displayed_jobs) if job["id"] == "test")
        dialog.jobs_table.selectRow(row)
        emitted = []
        dialog.start_selected_requested.connect(emitted.append)
        self.assertTrue(dialog.start_selected_button.isEnabled())
        dialog.start_selected_button.click()
        self.assertEqual([job["id"] for job in emitted], ["test"])
        self.assertEqual(dialog.jobs, jobs)
        dialog.set_running(True)
        self.assertFalse(dialog.start_selected_button.isEnabled())

    def test_selected_button_is_disabled_for_deferred_jobs_or_an_external_running_job(self):
        jobs = self.jobs()
        jobs[1]["status"] = "deferred"
        dialog = TrimExportQueueDialog(jobs)
        self.addCleanup(dialog.deleteLater)
        row = next(index for index, job in enumerate(dialog.displayed_jobs) if job["id"] == "test")
        dialog.jobs_table.selectRow(row)
        self.assertFalse(dialog.start_selected_button.isEnabled())
        jobs[1]["status"] = "queued"
        jobs[0]["status"] = "running"
        dialog.set_jobs(jobs)
        self.assertFalse(dialog.start_selected_button.isEnabled())

    def test_controller_refreshes_eligibility_and_starts_only_that_id(self):
        jobs = self.jobs()
        runner, client, dialog = Mock(is_running=False), Mock(), Mock()
        client.list_jobs.return_value = jobs
        controller = TrimExportQueueController(client, runner, Mock())
        controller.start_selected(dialog, jobs[1])
        client.list_jobs.assert_called_once_with()
        runner.start.assert_called_once_with(job_id="test")
        dialog.set_running.assert_called_once_with(True)
        client.defer.assert_not_called()
        client.resume.assert_not_called()

    def test_controller_does_not_run_a_job_whose_status_changed(self):
        jobs = self.jobs()
        runner, client, dialog = Mock(is_running=False), Mock(), Mock()
        client.list_jobs.return_value = [dict(job, status="deferred") for job in jobs]
        controller = TrimExportQueueController(client, runner, Mock())
        with patch("video_encoder_ui.trim_export_queue_controller.QtWidgets.QMessageBox.warning"):
            controller.start_selected(dialog, jobs[1])
        runner.start.assert_not_called()
        dialog.set_running.assert_not_called()

    def test_runner_passes_the_job_id_to_the_existing_worker_process(self):
        runner = TrimExportQueueRunner(executable="/app/video_encoder")
        with patch.object(runner.process, "start"):
            runner.start(job_id="test-id")
        self.assertEqual(runner.process.arguments(), ["run-trim-exports", "--job", "test-id"])
        self.assertIsNone(runner.inhibitor_executable)

    def test_selected_completion_does_not_claim_that_the_whole_queue_was_processed(self):
        controller = TrimExportQueueController(Mock(), Mock(is_running=False), Mock())
        controller.selected_job_id = "test"
        with patch("video_encoder_ui.trim_export_queue_controller.QtWidgets.QMessageBox.information") as info:
            controller.succeeded()
        self.assertIn("Les autres montages restent en attente", info.call_args.args[2])
        self.assertEqual(info.call_args.args[1], "Montage terminé")
        self.assertIsNone(controller.selected_job_id)
