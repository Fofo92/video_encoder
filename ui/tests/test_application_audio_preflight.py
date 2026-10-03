import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import MltFrameMonitor
    from video_encoder_ui.trim_export_queue_client import (
        TrimExportQueueError,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 or MLT is unavailable"
)
class ApplicationAudioPreflightTest(unittest.TestCase):
    def make_monitor(self, **attributes):
        project_archiver = Mock()
        project_archiver.archive.side_effect = (
            lambda project_path, output_path: project_path
        )
        defaults = {
            "close_after_preflight": False,
            "export_status_changed": Mock(),
            "audio_preflight_cancel_prompt_active": False,
            "deferred_audio_preflight_result": None,
            "pending_export_mode": "immediate",
            "trim_project_archiver": project_archiver,
            "confirm_audio_preflight": Mock(return_value=True),
        }
        defaults.update(attributes)
        return SimpleNamespace(**defaults)

    def test_checks_audio_before_starting_the_export(self):
        project_path = Path("/projects/movie.json")
        output_path = Path("/projects/movie.mkv")

        exporter = Mock(is_running=False)
        preflight = Mock(is_running=False)

        monitor = self.make_monitor(
            source_path=Path("/recordings/movie.ts"),
            trim_session=SimpleNamespace(segments=[object()]),
            project_path=project_path,
            trim_project_exporter=exporter,
            audio_preflight_runner=preflight,
            pending_export=None,
            save_project=Mock(return_value=project_path),
        )

        MltFrameMonitor.export_project(monitor)

        monitor.save_project.assert_called_once_with()
        preflight.start.assert_called_once_with(project_path)
        exporter.start.assert_not_called()
        self.assertEqual(
            monitor.pending_export,
            (project_path, output_path)
        )

    def test_defers_archiving_until_audio_is_confirmed(self):
        project_path = Path("/projects/movie.json")
        archived_project_path = Path(
            "/output/movie.json"
        )
        output_path = Path("/projects/movie.mkv")

        exporter = Mock(is_running=False)
        preflight = Mock(is_running=False)
        project_archiver = Mock()

        monitor = self.make_monitor(
            source_path=Path("/recordings/movie.ts"),
            trim_session=SimpleNamespace(
                segments=[object()]
            ),
            project_path=project_path,
            trim_project_exporter=exporter,
            audio_preflight_runner=preflight,
            trim_project_archiver=project_archiver,
            pending_export=None,
            save_project=Mock(
                return_value=project_path
            ),
        )

        MltFrameMonitor.export_project(
            monitor,
            queued=True,
        )

        monitor.save_project.assert_called_once_with()
        project_archiver.archive.assert_not_called()
        preflight.start.assert_called_once_with(
            project_path
        )
        preflight.start.assert_called_once_with(
            project_path
        )
        project_archiver.archive.assert_not_called()
        exporter.start.assert_not_called()
        self.assertEqual(
            monitor.pending_export,
            (
                project_path,
                output_path,
            ),
        )
        self.assertEqual(
            monitor.pending_export_mode,
            "queued",
        )

    def test_abandons_the_pending_export_when_preflight_fails(self):
        exporter = Mock()
        monitor = self.make_monitor(
            trim_project_exporter=exporter,
            pending_export=(
                Path("/projects/movie.json"),
                "/output/movie.mkv",
            ),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.warning"
        ) as warning:
            MltFrameMonitor.audio_preflight_failed(
                monitor,
                "ffmpeg failed",
            )

        self.assertIsNone(monitor.pending_export)
        exporter.start.assert_not_called()
        warning.assert_called_once_with(
            monitor,
            "Échec du contrôle audio",
            "ffmpeg failed",
        )

    def test_does_not_export_when_audio_confirmation_is_declined(self):
        exporter = Mock()
        confirmation = Mock(return_value=False)
        monitor = self.make_monitor(
            trim_project_exporter=exporter,
            confirm_audio_preflight=confirmation,
            pending_export=(
                Path("/projects/movie.json"),
                "/output/movie.mkv",
            ),
        )
        report = {
            "version": 1,
            "audio_checks": [
                {
                    "source": "/recordings/movie.ts",
                    "track_index": 1,
                    "language": "fra",
                    "analysis": {
                        "status": "inconclusive",
                        "sample_count": 0,
                        "mean_volume_db": None,
                        "max_volume_db": None,
                    },
                }
            ],
        }

        MltFrameMonitor.audio_preflight_succeeded(
            monitor,
            report,
        )

        confirmation.assert_called_once_with(
            report,
            "immediate",
        )
        exporter.start.assert_not_called()
        self.assertIsNone(monitor.pending_export)

    def test_exports_when_audio_confirmation_is_accepted(self):
        project_path = Path("/projects/movie.json")
        output_path = "/output/movie.mkv"
        exporter = Mock()

        monitor = self.make_monitor(
            trim_project_exporter=exporter,
            pending_export=(project_path, output_path),
        )
        report = {
            "version": 1,
            "audio_checks": [
                {
                    "source": "/recordings/movie.ts",
                    "track_index": 1,
                    "language": "fra",
                    "analysis": {
                        "status": "signal_detected",
                        "sample_count": 2_880_000,
                        "mean_volume_db": -25.0,
                        "max_volume_db": -3.0,
                    },
                }
            ],
        }

        MltFrameMonitor.audio_preflight_succeeded(
            monitor,
            report,
        )

        monitor.confirm_audio_preflight.assert_called_once_with(
            report,
            "immediate",
        )
        exporter.start.assert_called_once_with(
            project_path,
            output_path,
        )
        self.assertIsNone(monitor.pending_export)

    def test_enqueues_without_a_second_modal_confirmation(self):
        project_path = Path("/projects/movie.json")
        archived_project_path = Path(
            "/output/movie.json"
        )
        output_path = "/output/movie.mkv"
        exporter = Mock()
        queue_client = Mock()
        project_archiver = Mock()
        status_bar = Mock()
        project_archiver.archive.return_value = (
            archived_project_path
        )
        monitor = self.make_monitor(
            trim_project_archiver=project_archiver,
            trim_project_exporter=exporter,
            trim_export_queue_client=queue_client,
            pending_export=(project_path, output_path),
            pending_export_mode="queued",
            start_new_project_from_current_source=Mock(),
            close=Mock(),
            statusBar=Mock(return_value=status_bar),
        )
        report = {
            "version": 1,
            "audio_checks": [],
        }

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.information"
        ) as information:
            MltFrameMonitor.audio_preflight_succeeded(
                monitor,
                report,
            )

        project_archiver.archive.assert_called_once_with(
            project_path,
            output_path,
        )
        queue_client.enqueue.assert_called_once_with(
            archived_project_path,
            output_path,
        )

        exporter.start.assert_not_called()
        monitor.export_status_changed.assert_called_with(
            "queued"
        )
        information.assert_not_called()
        status_bar.showMessage.assert_called_once_with(
            f"Montage ajouté à la file : {output_path}",
            5_000,
        )

        monitor.start_new_project_from_current_source.assert_called_once_with()
        monitor.close.assert_not_called()
        self.assertIsNone(monitor.pending_export)
        self.assertIsNone(
            monitor.pending_export_mode
        )

    def test_reports_an_error_when_queueing_fails(self):
        project_path = Path("/projects/movie.json")
        archived_project_path = Path(
            "/output/movie.json"
        )
        output_path = "/output/movie.mkv"
        exporter = Mock()
        queue_client = Mock()
        queue_client.enqueue.side_effect = (
            TrimExportQueueError(
                "output already exists: /output/movie.mkv"
            )
        )
        project_archiver = Mock()
        project_archiver.archive.return_value = (
            archived_project_path
        )
        monitor = self.make_monitor(
            trim_project_archiver=project_archiver,
            trim_project_exporter=exporter,
            trim_export_queue_client=queue_client,
            pending_export=(project_path, output_path),
            pending_export_mode="queued",
            start_new_project_from_current_source=Mock(),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.warning"
        ) as warning:
            MltFrameMonitor.audio_preflight_succeeded(
                monitor,
                {
                    "audio_checks": [],
                },
            )

        queue_client.enqueue.assert_called_once_with(
            archived_project_path,
            output_path,
        )
        monitor.export_status_changed.assert_called_with(
            "failed"
        )
        warning.assert_called_once_with(
            monitor,
            "Mise en file impossible",
            "output already exists: /output/movie.mkv",
        )
        exporter.start.assert_not_called()
        monitor.start_new_project_from_current_source.assert_not_called()
        self.assertIsNone(monitor.pending_export)
        self.assertIsNone(monitor.pending_export_mode)

    def test_discards_pending_export_before_cancelling_preflight(self):
        preflight = Mock(is_running=True)
        monitor = self.make_monitor(
            audio_preflight_runner=preflight,
            pending_export=(
                Path("/projects/movie.json"),
                "/output/movie.mkv",
            ),
        )

        def cancel():
            self.assertIsNone(monitor.pending_export)
            return True

        preflight.cancel.side_effect = cancel

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ):
            accepted = MltFrameMonitor.cancel_audio_preflight(
                monitor
            )

        self.assertTrue(accepted)
        preflight.cancel.assert_called_once_with()
        self.assertIsNone(monitor.pending_export)

    def test_defers_closing_while_audio_preflight_is_running(self):
        event = Mock()
        monitor = self.make_monitor(
            audio_preflight_runner=Mock(is_running=True),
            close_after_preflight=False,
            cancel_audio_preflight=Mock(return_value=True),
            cancel_export=Mock(return_value=True),
            shutdown=Mock(),
        )

        MltFrameMonitor.closeEvent(monitor, event)

        monitor.cancel_audio_preflight.assert_called_once_with(
            quitting=True
        )
        self.assertTrue(monitor.close_after_preflight)
        event.ignore.assert_called_once_with()
        monitor.cancel_export.assert_not_called()
        monitor.shutdown.assert_not_called()

    def test_schedules_closing_after_preflight_finishes(self):
        for status in ("succeeded", "failed", "cancelled"):
            with self.subTest(status=status):
                monitor = self.make_monitor(
                    close_after_preflight=True,
                    pending_export=(
                        Path("/projects/movie.json"),
                        "/output/movie.mkv",
                    ),
                    close=Mock(),
                )

                with patch(
                    "video_encoder_ui.application."
                    "QtCore.QTimer.singleShot"
                ) as single_shot:
                    MltFrameMonitor.audio_preflight_status_changed(
                        monitor,
                        status,
                    )

                self.assertIsNone(monitor.pending_export)
                single_shot.assert_called_once_with(
                    0,
                    monitor.close,
                )
                monitor.close.assert_not_called()

    def test_cancel_button_routes_to_audio_preflight(self):
        monitor = self.make_monitor(
            audio_preflight_runner=Mock(is_running=True),
            trim_project_exporter=Mock(is_running=False),
            cancel_audio_preflight=Mock(return_value=True),
        )

        accepted = MltFrameMonitor.cancel_export(monitor)

        self.assertTrue(accepted)
        monitor.cancel_audio_preflight.assert_called_once_with(
            quitting=False
        )
        monitor.trim_project_exporter.cancel.assert_not_called()

    def test_editing_commands_are_ignored_while_busy(self):
        commands = [
            ("set_in_marker", ()),
            ("set_out_marker", ()),
            ("add_current_segment", ()),
            ("delete_segment", (0,)),
            ("select_segment", (0,)),
            ("save_project", ()),
        ]

        for status in ("running", "preflight", "confirming"):
            for name, arguments in commands:
                with self.subTest(status=status, command=name):
                    monitor = SimpleNamespace(export_status=status)

                    result = getattr(MltFrameMonitor, name)(
                        monitor,
                        *arguments,
                    )

                    self.assertIsNone(result)

    def test_does_not_offer_export_during_cancellation_confirmation(self):
        preflight = Mock(is_running=True)
        preflight.cancel.return_value = True

        monitor = self.make_monitor(
            audio_preflight_runner=preflight,
            trim_project_exporter=Mock(),
            pending_export=(
                Path("/projects/movie.json"),
                "/output/movie.mkv",
            ),
        )
        report = {"version": 1, "audio_checks": []}

        def answer_question(*arguments):
            if arguments[1] == "Interrompre le contrôle audio ?":
                preflight.is_running = False

                MltFrameMonitor.audio_preflight_succeeded(
                    monitor,
                    report,
                )

                return QtWidgets.QMessageBox.StandardButton.Yes

            return QtWidgets.QMessageBox.StandardButton.No

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            side_effect=answer_question,
        ) as question:
            accepted = MltFrameMonitor.cancel_audio_preflight(
                monitor
            )

        self.assertTrue(accepted)
        question.assert_called_once()
        self.assertIsNone(monitor.pending_export)
        monitor.trim_project_exporter.start.assert_not_called()

    def test_does_not_export_when_project_archiving_fails(
        self
    ):
        project_path = Path("/projects/movie.json")
        output_path = "/output/movie.mkv"
        exporter = Mock(is_running=False)
        archiver = Mock()
        archiver.archive.side_effect = OSError(
            "permission denied"
        )

        monitor = self.make_monitor(
            trim_project_exporter=exporter,
            trim_project_archiver=archiver,
            pending_export=(
                project_path,
                output_path,
            ),
            pending_export_mode="immediate",
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.warning"
        ) as warning:
            MltFrameMonitor.audio_preflight_succeeded(
                monitor,
                {
                    "audio_checks": [],
                },
            )

        archiver.archive.assert_called_once_with(
            project_path,
            output_path,
        )
        warning.assert_called_once_with(
            monitor,
            "Archivage du projet impossible",
            "permission denied",
        )
        exporter.start.assert_not_called()
        self.assertIsNone(
            monitor.pending_export
        )
        self.assertIsNone(
            monitor.pending_export_mode
        )

if __name__ == "__main__":
    unittest.main()
