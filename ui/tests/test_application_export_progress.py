import unittest
from types import SimpleNamespace
from unittest.mock import Mock

try:
    import mlt7
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        MltFrameMonitor,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 or MLT is unavailable"
)
class ApplicationExportProgressTest(unittest.TestCase):
    def make_monitor(self, stage, label):
        return SimpleNamespace(
            export_stage=None,
            export_step=0,
            export_total_steps=0,
            export_stage_label="",
            export_progress_bar=Mock(),
            export_stage_name=Mock(
                return_value=label
            ),
            update_export_progress_format=Mock(),
            update_export_elapsed=Mock(),
        )

    def test_only_shows_progress_for_measurable_stages(self):
        cases = [
            ("video", "Vidéo", True),
            ("audio", "Audio français", True),
            ("subtitles", "Sous-titres", False),
            ("remux", "Remuxage final", False),
        ]

        for stage, label, visible in cases:
            with self.subTest(stage=stage):
                monitor = self.make_monitor(
                    stage,
                    label
                )

                MltFrameMonitor.export_stage_changed(
                    monitor,
                    {
                        "stage": stage,
                        "step": 1,
                        "total": 5,
                    }
                )

                monitor.export_progress_bar.setVisible\
                    .assert_called_once_with(visible)

                if visible:
                    monitor.export_progress_bar.setRange\
                        .assert_called_once_with(0, 100)
                    monitor.export_progress_bar.setValue\
                        .assert_called_once_with(0)
                else:
                    monitor.export_progress_bar.setRange\
                        .assert_not_called()
                    monitor.export_progress_bar.setValue\
                        .assert_not_called()

    def test_describes_unmeasurable_progress(self):
        status_bar = Mock()
        monitor = SimpleNamespace(
            export_status="running",
            export_step=1,
            export_total_steps=5,
            export_stage="subtitles",
            export_stage_label="Sous-titres",
            statusBar=Mock(return_value=status_bar),
            format_elapsed_time=Mock(
                return_value="00:00:12"
            ),
        )

        MltFrameMonitor.update_export_elapsed(
            monitor
        )

        status_bar.showMessage.assert_called_once_with(
            (
                "Export : Étape 1/5 — Sous-titres — "
                "progression non mesurable — 00:00:12"
            )
        )


if __name__ == "__main__":
    unittest.main()
