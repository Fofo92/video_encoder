import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.source_quarantine_client import (
    SourceQuarantineClient,
    SourceQuarantineError,
)


class SourceQuarantineClientTest(unittest.TestCase):
    def test_quarantines_a_confirmed_source(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout=(
                    "Source moved to quarantine: "
                    "/commun/Quarantaine/movie.m2t\n"
                ),
                stderr="",
            )
        )
        client = SourceQuarantineClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        message = client.quarantine(
            Path("/commun/to_be_cut/movie.m2t")
        )

        runner.assert_called_once_with(
            [
                "/app/video_encoder",
                "quarantine-source",
                "/commun/to_be_cut/movie.m2t",
                "--confirm",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            message,
            "Source moved to quarantine: "
            "/commun/Quarantaine/movie.m2t",
        )

    def test_reports_a_quarantine_failure(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=1,
                stdout="",
                stderr=(
                    "source is not eligible: "
                    "active_trim_exports\n"
                ),
            )
        )
        client = SourceQuarantineClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        with self.assertRaisesRegex(
            SourceQuarantineError,
            "active_trim_exports",
        ):
            client.quarantine(
                "/commun/to_be_cut/movie.m2t"
            )


if __name__ == "__main__":
    unittest.main()
