import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        MltFrameMonitor,
    )
    from video_encoder_ui.trim_export_queue_client import (
        TrimExportQueueError,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class ApplicationTrimExportQueueTest(
    unittest.TestCase
):

    def test_prevents_closing_while_queue_is_running(self):
        monitor = SimpleNamespace(
            trim_export_queue_runner=SimpleNamespace(
                is_running=True,
            )
        )
        event = Mock()

        with patch(
            "video_encoder_ui.application."
            "QtWidgets.QMessageBox.information"
        ) as information:
            MltFrameMonitor.closeEvent(
                monitor,
                event,
            )

        event.ignore.assert_called_once_with()
        information.assert_called_once_with(
            monitor,
            "File en cours",
            (
                "La file des montages est en cours "
                "d’exécution.\n"
                "Attends sa fin avant de fermer "
                "video_encoder."
            ),
        )

    def test_delegates_queue_display_to_controller(self):
        queue_controller = Mock()
        monitor = SimpleNamespace(
            trim_export_queue_controller=(
                queue_controller
            )
        )

        MltFrameMonitor.show_trim_export_queue(
            monitor
        )

        queue_controller.show.assert_called_once_with()

if __name__ == "__main__":
    unittest.main()
