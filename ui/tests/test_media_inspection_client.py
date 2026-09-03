import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.media_inspection_client import (
    MediaInspectionClient,
    MediaInspectionError,
)


class MediaInspectionClientTest(unittest.TestCase):
    def test_inspects_a_media_source(self):
        source = {
            "path": "/commun/movie.m2t",
            "inspection": {
                "duration": 3600
            }
        }
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "format": (
                            "video_encoder."
                            "media_inspection"
                        ),
                        "version": 1,
                        "source": source
                    }
                ),
                stderr="",
            )
        )
        client = MediaInspectionClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        result = client.inspect(
            "/commun/movie.m2t"
        )

        runner.assert_called_once_with(
            [
                "/app/video_encoder",
                "inspect-media",
                "/commun/movie.m2t",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result, source)

    def test_reports_an_inspection_failure(self):
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=1,
                stdout="",
                stderr="source unavailable\n",
            )
        )
        client = MediaInspectionClient(
            executable="/app/video_encoder",
            runner=runner,
        )

        with self.assertRaisesRegex(
            MediaInspectionError,
            "source unavailable",
        ):
            client.inspect("/commun/movie.m2t")


if __name__ == "__main__":
    unittest.main()
