import unittest

from video_encoder_ui.ad_analysis_bounds import ad_analysis_bounds
from video_encoder_ui.trim_session import SegmentSelection, SourceReference, TrimSession


class AdAnalysisBoundsTest(unittest.TestCase):
    def setUp(self):
        self.session = TrimSession()
        self.session.add_source(SourceReference("source", "/capture.m2t"))

    def bounds(self, first=None, last=None):
        return ad_analysis_bounds(self.session, "source", first, last, 1000)

    def test_uses_the_saved_single_segment_after_markers_are_cleared(self):
        self.session.add_segment(SegmentSelection("source", 100, 900))
        self.assertEqual(self.bounds(), (100, 900))
        self.assertEqual(len(self.session.segments), 1)

    def test_explicit_markers_take_priority_over_an_existing_segment(self):
        self.session.add_segment(SegmentSelection("source", 100, 900))
        self.assertEqual(self.bounds(200, 800), (200, 800))

    def test_does_not_silently_replace_partial_or_invalid_markers_with_a_segment(self):
        self.session.add_segment(SegmentSelection("source", 100, 900))
        for first, last in [(None, 800), (200, None), (800, 200), (-1, 800), (200, 1000)]:
            with self.subTest(first=first, last=last):
                self.assertIsNone(self.bounds(first, last))

    def test_requires_explicit_markers_for_a_montage_with_several_segments(self):
        self.session.add_segment(SegmentSelection("source", 100, 200))
        self.session.add_segment(SegmentSelection("source", 300, 900))
        self.assertIsNone(self.bounds())
        self.assertEqual(self.bounds(100, 900), (100, 900))

    def test_refuses_a_segment_from_another_source_or_outside_the_current_source(self):
        self.session.add_source(SourceReference("other", "/other.m2t"))
        self.session.add_segment(SegmentSelection("other", 100, 900))
        self.assertIsNone(self.bounds())
        self.session.clear_segments()
        self.session.add_segment(SegmentSelection("source", 100, 1200))
        self.assertIsNone(self.bounds())

    def test_without_markers_or_segments_no_envelope_is_inferred(self):
        self.assertIsNone(self.bounds())


if __name__ == "__main__":
    unittest.main()
