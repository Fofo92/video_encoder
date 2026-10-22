import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

from video_encoder_ui.trim_export_queue_client import TrimExportQueueClient
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession

if QtWidgets is not None:
    from video_encoder_ui.application import MltFrameMonitor
    from video_encoder_ui.trim_export_queue_controller import TrimExportQueueController
    from video_encoder_ui.trim_export_queue_dialog import TrimExportQueueDialog


class QueueCommandTest(unittest.TestCase):
    def test_sends_distinct_commands_for_deferral_deletion_and_destination(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout="ok", stderr=""))
        client = TrimExportQueueClient(executable="/encoder", runner=runner)
        client.defer("id")
        client.resume("id")
        client.remove("id")
        client.delete_project("id")
        client.set_output("id", "/new/output.mkv")
        self.assertEqual([call.args[0][1:] for call in runner.call_args_list], [
            ["defer-job", "id"], ["resume-job", "id"], ["delete-job", "id"],
            ["delete-job", "id", "--delete-project"], ["set-job-output", "id", "--output", "/new/output.mkv"],
        ])


@unittest.skipIf(QtWidgets is None, "PySide6 is unavailable")
class QueueControllerUsabilityTest(unittest.TestCase):
    def controller(self):
        controller = TrimExportQueueController(client=Mock(), runner=Mock(is_running=False), dialog_class=Mock())
        controller.refresh = Mock()
        return controller

    def test_reporting_and_reactivation_do_not_delete_the_task(self):
        controller = self.controller()
        dialog = Mock()
        controller.defer(dialog, {"id": "job", "status": "queued"})
        controller.defer(dialog, {"id": "job", "status": "deferred"})
        controller.client.defer.assert_called_once_with("job")
        controller.client.resume.assert_called_once_with("job")
        controller.client.remove.assert_not_called()

    def test_updates_output_without_enqueuing_a_duplicate(self):
        controller = self.controller()
        with patch("video_encoder_ui.trim_export_queue_controller.select_project_output", return_value=Path("/new/name.mkv")):
            controller.change_output(Mock(), {"id": "job", "status": "queued", "output_path": "/old/name.mkv"})
        controller.client.set_output.assert_called_once_with("job", Path("/new/name.mkv"))
        controller.client.enqueue.assert_not_called()

    def test_refuses_destination_change_while_the_queue_runs(self):
        controller = self.controller()
        controller.runner.is_running = True
        controller.change_output(Mock(), {"id": "job", "status": "queued"})
        controller.client.set_output.assert_not_called()

    def test_json_deletion_requires_explicit_confirmation(self):
        controller = self.controller()
        with patch("video_encoder_ui.trim_export_queue_controller.QtWidgets.QMessageBox.question", return_value=QtWidgets.QMessageBox.StandardButton.No):
            controller.delete_project(Mock(), {"id": "job", "status": "queued", "input_path": "/project.json"})
        controller.client.delete_project.assert_not_called()


@unittest.skipIf(QtWidgets is None, "PySide6 is unavailable")
class LoadedProjectDestinationTest(unittest.TestCase):
    def monitor(self, output):
        return SimpleNamespace(
            project_path=Path("/old/project.json"), source_path=Path("/capture.m2t"),
            trim_session=SimpleNamespace(segments=[object()]),
            trim_project_exporter=Mock(is_running=False), audio_preflight_runner=Mock(is_running=False),
            pending_export=None, save_project=Mock(return_value=Path("/old/project.json")),
            write_project=Mock(side_effect=lambda path: Path(path)),
            select_output_path=Mock(return_value=output), export_status_changed=Mock(),
        )

    def test_requeued_existing_project_uses_the_new_output_directory(self):
        monitor = self.monitor(Path("/new/name.mkv"))
        MltFrameMonitor.export_project(monitor, queued=True)
        monitor.select_output_path.assert_called_once_with(Path("/old/project.mkv"))
        self.assertEqual(monitor.pending_export, (Path("/new/name.json"), Path("/new/name.mkv")))
        monitor.audio_preflight_runner.start.assert_called_once_with(Path("/new/name.json"))
        monitor.write_project.assert_called_once_with(Path("/new/name.json"))
        monitor.save_project.assert_not_called()

    def test_cancelled_destination_does_not_start_audio_or_enqueue(self):
        monitor = self.monitor(None)
        MltFrameMonitor.export_project(monitor, queued=True)
        monitor.audio_preflight_runner.start.assert_not_called()
        monitor.write_project.assert_not_called()
        self.assertIsNone(monitor.pending_export)


@unittest.skipIf(QtWidgets is None, "PySide6 is unavailable")
class MarkerModeTest(unittest.TestCase):
    def monitor(self):
        session = TrimSession()
        session.add_source(SourceReference("source", "/capture.m2t"))
        segment = session.add_segment(SegmentSelection("source", 10, 20))
        monitor = SimpleNamespace(
            source_id="source", trim_session=session,
            segment_list=SimpleNamespace(currentRow=Mock(return_value=0), selectedItems=Mock(return_value=[object()])),
            export_status="idle", editing_segment_index=None, editing_segment=None,
            nudge_marker_selector=Mock(), nudge_backward_button=Mock(), nudge_forward_button=Mock(),
            nudge_shortcuts=[Mock(), Mock()], in_button=Mock(), out_button=Mock(),
            save_project_action=Mock(), export_project_action=Mock(), queue_export_action=Mock(),
            clear_active_markers=Mock(),
        )
        return monitor, segment

    def test_disables_adjustment_in_navigation_mode(self):
        monitor, _ = self.monitor()
        MltFrameMonitor.update_marker_edit_controls(monitor)
        monitor.nudge_backward_button.setEnabled.assert_called_once_with(False)
        monitor.nudge_forward_button.setEnabled.assert_called_once_with(False)
        monitor.nudge_marker_selector.setEnabled.assert_called_once_with(True)

    def test_edit_mode_is_exclusive_and_blocks_saving_until_apply(self):
        monitor, segment = self.monitor()
        monitor.editing_segment_index = 0
        monitor.editing_segment = segment
        MltFrameMonitor.update_marker_edit_controls(monitor)
        monitor.nudge_forward_button.setEnabled.assert_called_once_with(True)
        monitor.in_button.setEnabled.assert_called_once_with(False)
        monitor.queue_export_action.setEnabled.assert_called_once_with(False)

    def test_leaves_edit_mode_when_another_segment_is_selected(self):
        monitor, segment = self.monitor()
        monitor.editing_segment_index = 0
        monitor.editing_segment = segment
        monitor.trim_session.add_segment(SegmentSelection("source", 30, 40))
        monitor.segment_list.currentRow.return_value = 1
        MltFrameMonitor.update_marker_edit_controls(monitor)
        monitor.clear_active_markers.assert_called_once_with()

    def test_ctrl_nudge_does_nothing_in_navigation_mode(self):
        monitor, _ = self.monitor()
        monitor.nudge_marker_selector.currentIndex.return_value = 0
        monitor.in_position, monitor.out_position = 10, 20
        MltFrameMonitor.nudge_marker(monitor, 1)
        self.assertEqual(monitor.in_position, 10)


@unittest.skipIf(QtWidgets is None, "PySide6 is unavailable")
class QueueEligibilityTest(unittest.TestCase):
    def test_running_job_actions_are_disabled(self):
        dialog = SimpleNamespace(
            selected_job=Mock(return_value={"id": "job", "status": "running"}),
            remove_button=Mock(), defer_button=Mock(), output_button=Mock(), delete_project_button=Mock(),
            running=True, jobs=[], set_action_icon=Mock(),
        )
        TrimExportQueueDialog.update_remove_button(dialog)
        for name in ["remove_button", "defer_button", "output_button", "delete_project_button"]:
            getattr(dialog, name).setEnabled.assert_called_once_with(False)

    def test_deferred_job_is_reactivated_instead_of_reenqueued(self):
        dialog = SimpleNamespace(
            selected_job=Mock(return_value={"id": "job", "status": "deferred"}),
            remove_button=Mock(), defer_button=Mock(), output_button=Mock(), delete_project_button=Mock(),
            running=False, jobs=[], set_action_icon=Mock(),
        )
        TrimExportQueueDialog.update_remove_button(dialog)
        dialog.defer_button.setText.assert_called_once_with("Réactiver")
        dialog.defer_button.setEnabled.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
