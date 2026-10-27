import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
    import mlt7
except ModuleNotFoundError as error:
    if error.name not in {"PySide6", "mlt7"}:
        raise
    raise unittest.SkipTest("PySide6 or MLT is unavailable") from error

from video_encoder_ui import application


class VidbIdentificationActionTest(unittest.TestCase):
    def test_new_montage_identification_starts_queue_preparation_without_saving_first(self):
        monitor = SimpleNamespace(export_status="idle", project_path=None,
            source_path=Path("/commun/to_be_cut/Nouveau film.m2t"), trim_session=object(),
            trim_project_writer=object(), save_project=Mock(side_effect=AssertionError("must not save")),
            export_project=Mock())
        with patch.object(application, "review_montage_identification", return_value=True) as review:
            application.MltFrameMonitor.review_vidb_project(monitor)
        monitor.save_project.assert_not_called()
        monitor.export_project.assert_called_once_with(queued=True, identified_review=True)
        review.assert_called_once_with(monitor, monitor.trim_session, monitor.source_path,
                                       Path("/videos/Nouveau film.json"), monitor.trim_project_writer)

    def test_existing_project_keeps_its_current_location_for_identification(self):
        monitor = SimpleNamespace(export_status="idle", project_path=Path("/videos/Films/Film.json"),
            source_path=Path("/commun/to_be_cut/Film.m2t"), trim_session=object(), trim_project_writer=object(),
            export_project=Mock())
        with patch.object(application, "review_montage_identification", return_value=True) as review:
            application.MltFrameMonitor.review_vidb_project(monitor)
        self.assertEqual(monitor.project_path, review.call_args.args[3])
        monitor.export_project.assert_called_once_with(queued=True, identified_review=True)
