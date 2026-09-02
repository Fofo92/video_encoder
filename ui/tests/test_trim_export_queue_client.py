import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.trim_export_queue_client import (
    TrimExportQueueClient,
    TrimExportQueueError,
)


class TrimExportQueueClientTest(unittest.TestCase):
    def test_enqueues_a_trim_export(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout=(
                    "Enqueued trim export: trim-1 "
                    "(movie.json -> movie.mkv)\n"
                ),
                stderr="",
            )
        )
        client = TrimExportQueueClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        output = client.enqueue(
            Path("movie.json"),
            Path("movie.mkv"),
        )

        runner.assert_called_once_with(
            [
                "/app/video_encoder",
                "enqueue-trim-export",
                "movie.json",
                "--output",
                "movie.mkv",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            output,
            "Enqueued trim export: trim-1 "
            "(movie.json -> movie.mkv)",
        )

    def test_reports_an_enqueue_failure(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=1,
                stdout="",
                stderr=(
                    "output already exists: "
                    "movie.mkv\n"
                ),
            )
        )
        client = TrimExportQueueClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        with self.assertRaisesRegex(
            TrimExportQueueError,
            "output already exists: movie.mkv",
        ):
            client.enqueue(
                "movie.json",
                "movie.mkv",
            )


if __name__ == "__main__":
    unittest.main()
