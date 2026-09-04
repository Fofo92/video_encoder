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

    def test_lists_only_trim_export_jobs(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout=(
                    '{"format":"video_encoder.job_list",'
                    '"version":1,'
                    '"jobs":['
                    '{"id":"trim-1",'
                    '"kind":"trim_export",'
                    '"input_path":"movie.json",'
                    '"output_path":"movie.mkv",'
                    '"status":"queued"},'
                    '{"id":"encoding-1",'
                    '"kind":"encoding",'
                    '"input_path":"source.m2t",'
                    '"output_path":null,'
                    '"status":"done"}'
                    "]}"
                ),
                stderr="",
            )
        )
        client = TrimExportQueueClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        jobs = client.list_jobs()

        runner.assert_called_once_with(
            [
                "/app/video_encoder",
                "list",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            jobs,
            [
                {
                    "id": "trim-1",
                    "kind": "trim_export",
                    "input_path": "movie.json",
                    "output_path": "movie.mkv",
                    "status": "queued",
                }
            ],
        )

    def test_reports_a_listing_failure(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="database unavailable\n",
            )
        )
        client = TrimExportQueueClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        with self.assertRaisesRegex(
            TrimExportQueueError,
            "database unavailable",
        ):
            client.list_jobs()

    def test_rejects_an_invalid_listing_response(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout="not JSON",
                stderr="",
            )
        )
        client = TrimExportQueueClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        with self.assertRaisesRegex(
            TrimExportQueueError,
            "invalid trim export queue response",
        ):
            client.list_jobs()

if __name__ == "__main__":
    unittest.main()
