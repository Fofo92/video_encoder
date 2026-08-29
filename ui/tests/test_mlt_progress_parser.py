import unittest

from video_encoder_ui.mlt_progress_parser import (
    MltProgressParser,
)


class MltProgressParserTest(unittest.TestCase):
    def test_extracts_distinct_percentages(self):
        parser = MltProgressParser()

        percentages, diagnostics = parser.feed(
            "Current Frame: 1, percentage: 1\n"
            "Current Frame: 2, percentage: 1\n"
            "Current Frame: 3, percentage: 2\n"
        )

        self.assertEqual(
            percentages,
            [1, 2]
        )
        self.assertEqual(
            diagnostics,
            []
        )

    def test_preserves_incomplete_lines_between_chunks(self):
        parser = MltProgressParser()

        first_percentages, _diagnostics = parser.feed(
            "Current Frame: 10, percen"
        )
        second_percentages, _diagnostics = parser.feed(
            "tage: 42\n"
        )

        self.assertEqual(
            first_percentages,
            []
        )
        self.assertEqual(
            second_percentages,
            [42]
        )

    def test_keeps_non_progress_output_as_diagnostics(self):
        parser = MltProgressParser()

        percentages, diagnostics = parser.feed(
            "warning from melt\n"
        )

        self.assertEqual(percentages, [])
        self.assertEqual(
            diagnostics,
            ["warning from melt"]
        )


if __name__ == "__main__":
    unittest.main()
