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


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 or MLT is unavailable"
)
class ApplicationAudioPreflightTest(unittest.TestCase):
    def make_monitor(self, **attributes):
        defaults = {
            "close_after_preflight": False,
            "export_status_changed": Mock(),
            "audio_preflight_cancel_prompt_active": False,
            "deferred_audio_preflight_result": None,
            "pending_export_mode": "immediate",
        }
        defaults.update(attributes)
        return SimpleNamespace(**defaults)

    def test_checks_audio_before_starting_the_export(self):
        project_path = Path("/projects/movie.json")
        output_path = "/output/movie.mkv"

        exporter = Mock(is_running=False)
        preflight = Mock(is_running=False)

        monitor = self.make_monitor(
            source_path=Path("/recordings/movie.ts"),
            trim_session=SimpleNamespace(segments=[object()]),
            project_path=project_path,
            trim_project_exporter=exporter,
            audio_preflight_runner=preflight,
            pending_export=None,
            write_project=Mock(return_value=project_path),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getSaveFileName",
            return_value=(output_path, ""),
        ):
            MltFrameMonitor.export_project(monitor)

        monitor.write_project.assert_called_once_with(
            project_path
        )
        preflight.start.assert_called_once_with(project_path)
        exporter.start.assert_not_called()
        self.assertEqual(
            monitor.pending_export,
            (project_path, output_path)
        )

    def test_checks_audio_before_queuing_the_export(self):
        project_path = Path("/projects/movie.json")
        output_path = "/output/movie.mkv"

        exporter = Mock(is_running=False)
        preflight = Mock(is_running=False)

        monitor = self.make_monitor(
            source_path=Path("/recordings/movie.ts"),
            trim_session=SimpleNamespace(
                segments=[object()]
            ),
            project_path=project_path,
            trim_project_exporter=exporter,
            audio_preflight_runner=preflight,
            pending_export=None,
            write_project=Mock(
                return_value=project_path
            ),
        )

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QFileDialog.getSaveFileName",
            return_value=(output_path, ""),
        ):
            MltFrameMonitor.export_project(
                monitor,
                queued=True,
            )

        preflight.start.assert_called_once_with(
            project_path
        )
        exporter.start.assert_not_called()
        self.assertEqual(
            monitor.pending_export,
            (project_path, output_path),
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
        monitor = self.make_monitor(
            trim_project_exporter=exporter,
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

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.StandardButton.No,
        ) as question:
            MltFrameMonitor.audio_preflight_succeeded(
                monitor,
                report,
            )

        question.assert_called_once()
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

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.question",
            return_value=QtWidgets.QMessageBox.StandardButton.Yes,
        ) as question:
            MltFrameMonitor.audio_preflight_succeeded(
                monitor,
                report,
            )

        question.assert_called_once()
        self.assertEqual(
            question.call_args.args[-1],
            QtWidgets.QMessageBox.StandardButton.No,
        )
        exporter.start.assert_called_once_with(
            project_path,
            output_path,
        )
        self.assertIsNone(monitor.pending_export)

    def test_enqueues_when_queue_mode_is_selected(self):
        project_path = Path("/projects/movie.json")
        output_path = "/output/movie.mkv"
        exporter = Mock()
        queue_client = Mock()

        monitor = self.make_monitor(
            trim_project_exporter=exporter,
            trim_export_queue_client=queue_client,
            pending_export=(project_path, output_path),
            pending_export_mode="queued",
        )
        report = {
            "version": 1,
            "audio_checks": [],
        }

        with (
            patch(
                "video_encoder_ui.application."
                "QtWidgets.QMessageBox.question",
                return_value=(
                    QtWidgets.QMessageBox.StandardButton.Yes
                ),
            ),
            patch(
                "video_encoder_ui.application."
                "QtWidgets.QMessageBox.information"
            ) as information,
        ):
            MltFrameMonitor.audio_preflight_succeeded(
                monitor,
                report,
            )

        queue_client.enqueue.assert_called_once_with(
            project_path,
            output_path,
        )
        exporter.start.assert_not_called()
        monitor.export_status_changed.assert_called_with(
            "queued"
        )
        information.assert_called_once_with(
            monitor,
            "Montage ajouté à la file",
            (
                "Le montage sera exporté vers :\n"
                f"{output_path}"
            ),
        )
        self.assertIsNone(monitor.pending_export)
        self.assertIsNone(
            monitor.pending_export_mode
        )

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

if __name__ == "__main__":
    unittest.main()
