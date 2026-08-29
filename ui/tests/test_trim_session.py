import unittest

from video_encoder_ui.trim_session import (
    SegmentSelection,
    SourceReference,
    TrimSession,
)


class TrimSessionTest(unittest.TestCase):
    def setUp(self):
        self.session = TrimSession()
        self.session.add_source(
            SourceReference(
                identifier="A",
                path="/commun/source-a.m2t"
            )
        )
        self.session.add_source(
            SourceReference(
                identifier="C",
                path="/commun/source-c.m2t"
            )
        )

    def test_preserves_segment_order_across_sources(self):
        first = SegmentSelection(
            source_id="A",
            start_frame=0,
            end_frame=1499
        )
        replacement = SegmentSelection(
            source_id="C",
            start_frame=3000,
            end_frame=4499
        )
        last = SegmentSelection(
            source_id="A",
            start_frame=5000,
            end_frame=7999
        )

        self.session.add_segment(first)
        self.session.add_segment(replacement)
        self.session.add_segment(last)

        self.assertEqual(
            self.session.segments,
            (first, replacement, last)
        )

    def test_rejects_a_segment_with_an_unknown_source(self):
        segment = SegmentSelection(
            source_id="unknown",
            start_frame=0,
            end_frame=100
        )

        with self.assertRaisesRegex(
            ValueError,
            "segment source is unknown"
        ):
            self.session.add_segment(segment)

    def test_rejects_incomplete_frame_boundaries(self):
        with self.assertRaisesRegex(
            ValueError,
            "end frame must be after start frame"
        ):
            SegmentSelection(
                source_id="A",
                start_frame=100,
                end_frame=100
            )

    def test_builds_the_trim_session_document(self):
        self.session.add_segment(
            SegmentSelection(
                source_id="A",
                start_frame=0,
                end_frame=1499
            )
        )
        self.session.add_segment(
            SegmentSelection(
                source_id="C",
                start_frame=3000,
                end_frame=4499
            )
        )

        self.assertEqual(
            self.session.to_document(),
            {
                "format": "video_encoder.trim_session",
                "version": 1,
                "sources": [
                    {
                        "id": "A",
                        "path": "/commun/source-a.m2t"
                    },
                    {
                        "id": "C",
                        "path": "/commun/source-c.m2t"
                    }
                ],
                "timeline": [
                    {
                        "source_id": "A",
                        "start_frame": 0,
                        "end_frame": 1499
                    },
                    {
                        "source_id": "C",
                        "start_frame": 3000,
                        "end_frame": 4499
                    }
                ]
            }
        )

    def test_removes_a_segment(self):
        segment = SegmentSelection(
            source_id="A",
            start_frame=100,
            end_frame=200
        )
        self.session.add_segment(segment)

        self.session.remove_segment(segment)

        self.assertEqual(
            self.session.segments,
            ()
        )


if __name__ == "__main__":
    unittest.main()
