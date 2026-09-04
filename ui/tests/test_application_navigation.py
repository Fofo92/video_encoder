import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import (
        MltFrameMonitor,
    )


@unittest.skipIf(
    QtWidgets is None,
    "PySide6 is unavailable",
)
class ApplicationNavigationTest(unittest.TestCase):
    def test_goes_to_source_boundaries(self):
        monitor = SimpleNamespace(
            frame_source=SimpleNamespace(
                length=1_000
            ),
            show_frame=Mock(),
        )

        MltFrameMonitor.go_to_source_start(
            monitor
        )
        MltFrameMonitor.go_to_source_end(
            monitor
        )

        self.assertEqual(
            monitor.show_frame.call_args_list,
            [
                call(0),
                call(999),
            ]
        )

    def test_goes_to_selected_segment_boundaries(self):
        segment = SimpleNamespace(
            source_id="source",
            start_frame=100,
            end_frame=200,
        )
        monitor = SimpleNamespace(
            source_id="source",
            trim_session=SimpleNamespace(
                segments=(segment,)
            ),
            segment_list=SimpleNamespace(
                currentRow=Mock(
                    return_value=0
                )
            ),
            show_frame=Mock(),
        )

        MltFrameMonitor.go_to_segment_start(
            monitor
        )
        MltFrameMonitor.go_to_segment_end(
            monitor
        )

        self.assertEqual(
            monitor.show_frame.call_args_list,
            [
                call(100),
                call(200),
            ]
        )

    def test_ignores_segment_navigation_without_selection(self):
        monitor = SimpleNamespace(
            source_id="source",
            trim_session=SimpleNamespace(
                segments=()
            ),
            segment_list=SimpleNamespace(
                currentRow=Mock(
                    return_value=-1
                )
            ),
            show_frame=Mock(),
        )

        MltFrameMonitor.go_to_segment_start(
            monitor
        )
        MltFrameMonitor.go_to_segment_end(
            monitor
        )

        monitor.show_frame.assert_not_called()


if __name__ == "__main__":
    unittest.main()
