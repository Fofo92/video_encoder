import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import mlt7  # noqa: F401
    from PySide6 import QtWidgets
except ModuleNotFoundError:
    QtWidgets = None

if QtWidgets is not None:
    from video_encoder_ui.application import MltFrameMonitor


@unittest.skipIf(QtWidgets is None, "PySide6 or MLT is unavailable")
class IdentificationQueueFlowTest(unittest.TestCase):
    def test_confirmed_identification_starts_queue_preparation(self):
        monitor = SimpleNamespace(
            export_status="idle", source_path=Path("/commun/source.m2t"),
            project_path=None, trim_session=object(), trim_project_writer=object(),
            export_project=Mock())
        with patch("video_encoder_ui.application.review_montage_identification", return_value=True):
            MltFrameMonitor.review_vidb_project(monitor)
        monitor.export_project.assert_called_once_with(queued=True, identified_review=True)

    def test_closing_identification_does_not_start_queue_preparation(self):
        monitor = SimpleNamespace(
            export_status="idle", source_path=Path("/commun/source.m2t"),
            project_path=None, trim_session=object(), trim_project_writer=object(),
            export_project=Mock())
        with patch("video_encoder_ui.application.review_montage_identification", return_value=False):
            MltFrameMonitor.review_vidb_project(monitor)
        monitor.export_project.assert_not_called()

    def test_cancel_destination_returns_to_episode_choices(self):
        metadata = {"record_kind": "episode"}
        monitor = SimpleNamespace(
            trim_project_writer=SimpleNamespace(vidb_result={"metadata": metadata}),
            project_path=None)
        with patch("video_encoder_ui.episode_destination.suggested_episode_output", return_value=Path("/videos/a.mkv")), \
             patch("video_encoder_ui.application.select_project_output", side_effect=[None, Path("/videos/b.mkv")]), \
             patch("video_encoder_ui.catalogue_destination.confirm_episode_destination", return_value=Path("/videos/b.mkv")) as choices:
            result = MltFrameMonitor.select_output_path(monitor, Path("/videos/a.mkv"), identified_review=True)
        self.assertEqual(Path("/videos/b.mkv"), result)
        choices.assert_called_once()


if __name__ == "__main__":
    unittest.main()
