import unittest

from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession


class TrimSessionReplacementTest(unittest.TestCase):
    def setUp(self):
        self.session = TrimSession()
        self.session.add_source(SourceReference("source", "/capture.m2t"))
        self.original = tuple(
            SegmentSelection("source", a, b)
            for a, b in [(0, 100), (200, 300), (400, 500)]
        )
        for segment in self.original:
            self.session.add_segment(segment)

    def test_replaces_in_place_without_reordering_other_segments(self):
        replacement = SegmentSelection("source", 210, 290)
        self.session.replace_segment(1, replacement)
        self.assertEqual(
            self.session.segments,
            (self.original[0], replacement, self.original[2]),
        )

    def test_rejects_unknown_source_without_changing_the_montage(self):
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.session.replace_segment(1, SegmentSelection("missing", 210, 290))
        self.assertEqual(self.session.segments, self.original)

    def test_rejects_invalid_indices_without_changing_the_montage(self):
        for index in [-1, 3]:
            with self.assertRaisesRegex(ValueError, "index"):
                self.session.replace_segment(index, self.original[0])
        self.assertEqual(self.session.segments, self.original)


if __name__ == "__main__":
    unittest.main()
