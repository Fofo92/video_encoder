
import json
import tempfile
import unittest
from pathlib import Path

from video_encoder_ui.trim_project_file_reader import (
    TrimProjectFileReader,
)
from video_encoder_ui.trim_session import (
    SegmentSelection,
    SourceReference,
)


class TrimProjectFileReaderTest(unittest.TestCase):
    def load(self, document):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(
                json.dumps(document),
                encoding="utf-8"
            )

            return TrimProjectFileReader().load(
                path
            )

    def test_restores_sources_and_segment_order(self):
        session = self.load(
            {
                "format": "video_encoder.trim_project",
                "version": 1,
                "timeline": [
                    {
                        "type": "segment",
                        "source": "/commun/source-a.m2t",
                        "start_frame": 0,
                        "end_frame": 1499
                    },
                    {
                        "type": "segment",
                        "source": "/commun/source-c.m2t",
                        "start_frame": 3000,
                        "end_frame": 4499
                    },
                    {
                        "type": "segment",
                        "source": "/commun/source-a.m2t",
                        "start_frame": 5000,
                        "end_frame": 7999
                    }
                ]
            }
        )

        self.assertEqual(
            session.sources,
            (
                SourceReference(
                    "source",
                    Path("/commun/source-a.m2t")
                ),
                SourceReference(
                    "source_1",
                    Path("/commun/source-c.m2t")
                )
            )
        )
        self.assertEqual(
            session.segments,
            (
                SegmentSelection(
                    "source",
                    0,
                    1499
                ),
                SegmentSelection(
                    "source_1",
                    3000,
                    4499
                ),
                SegmentSelection(
                    "source",
                    5000,
                    7999
                )
            )
        )

    def test_rejects_an_unknown_version(self):
        with self.assertRaisesRegex(
            ValueError,
            "unsupported trim project version"
        ):
            self.load(
                {
                    "format": "video_encoder.trim_project",
                    "version": 2,
                    "timeline": []
                }
            )

    def test_rejects_gaps_until_the_editor_supports_them(self):
        with self.assertRaisesRegex(
            ValueError,
            "gaps are not supported by the editor"
        ):
            self.load(
                {
                    "format": "video_encoder.trim_project",
                    "version": 1,
                    "timeline": [
                        {
                            "type": "gap",
                            "frame_count": 50
                        }
                    ]
                }
            )


if __name__ == "__main__":
    unittest.main()
