import unittest
from unittest.mock import Mock

from video_encoder_ui.source_quarantine_client import (
    SourceQuarantineError,
)
from video_encoder_ui.source_quarantine_controller import (
    SourceQuarantineController,
)


class SourceQuarantineControllerTest(unittest.TestCase):
    def setUp(self):
        self.client = Mock()
        self.select_source = Mock()
        self.confirm = Mock()
        self.report_success = Mock()
        self.report_failure = Mock()

        self.controller = SourceQuarantineController(
            client=self.client,
            select_source=self.select_source,
            confirm=self.confirm,
            report_success=self.report_success,
            report_failure=self.report_failure,
        )

    def test_quarantines_a_confirmed_source(self):
        source_path = "/commun/to_be_cut/movie.m2t"
        self.select_source.return_value = source_path
        self.confirm.return_value = True
        self.client.quarantine.return_value = (
            "Source moved to quarantine"
        )

        self.controller.run()

        self.confirm.assert_called_once_with(source_path)
        self.client.quarantine.assert_called_once_with(
            source_path
        )
        self.report_success.assert_called_once_with(
            source_path
        )
        self.report_failure.assert_not_called()

    def test_does_nothing_when_selection_is_cancelled(self):
        self.select_source.return_value = None

        self.controller.run()

        self.confirm.assert_not_called()
        self.client.quarantine.assert_not_called()
        self.report_success.assert_not_called()
        self.report_failure.assert_not_called()

    def test_does_not_move_an_unconfirmed_source(self):
        source_path = "/commun/to_be_cut/movie.m2t"
        self.select_source.return_value = source_path
        self.confirm.return_value = False

        self.controller.run()

        self.client.quarantine.assert_not_called()
        self.report_success.assert_not_called()
        self.report_failure.assert_not_called()

    def test_reports_a_quarantine_failure(self):
        source_path = "/commun/to_be_cut/movie.m2t"
        self.select_source.return_value = source_path
        self.confirm.return_value = True
        self.client.quarantine.side_effect = (
            SourceQuarantineError(
                "active_trim_exports"
            )
        )

        self.controller.run()

        self.report_failure.assert_called_once_with(
            "active_trim_exports"
        )
        self.report_success.assert_not_called()


if __name__ == "__main__":
    unittest.main()
