import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from video_encoder_ui.trim_project_file_writer import (
    TrimProjectFileWriter,
)


class TrimProjectFileWriterTest(unittest.TestCase):
    def test_writes_the_canonical_project_returned_by_ruby(self):
        document = {
            "format": "video_encoder.trim_project",
            "version": 1,
            "timeline": [
                {
                    "type": "segment",
                    "source": "/commun/source-a.m2t",
                    "start_frame": 1500,
                    "end_frame": 2999
                }
            ]
        }

        bridge = Mock()
        bridge.convert.return_value = document

        writer = TrimProjectFileWriter(bridge)

        with tempfile.TemporaryDirectory() as directory:
            destination = (
                Path(directory)
                / "montage.json"
            )

            result = writer.save(
                Mock(),
                destination
            )

            self.assertEqual(result, destination)
            self.assertEqual(
                json.loads(
                    destination.read_text(
                        encoding="utf-8"
                    )
                ),
                document
            )


if __name__ == "__main__":
    unittest.main()
