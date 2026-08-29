import unittest

from video_encoder_ui.export_event_parser import (
    ExportEventParser,
)


class ExportEventParserTest(unittest.TestCase):
    def test_extracts_a_structured_export_event(self):
        parser = ExportEventParser()

        events, diagnostics = parser.feed(
            "VIDEO_ENCODER_EXPORT_EVENT "
            '{"stage":"audio","step":2,"total":5}\n'
        )

        self.assertEqual(
            events,
            [
                {
                    "stage": "audio",
                    "step": 2,
                    "total": 5
                }
            ]
        )
        self.assertEqual(diagnostics, [])

    def test_preserves_an_event_split_between_chunks(self):
        parser = ExportEventParser()

        first_events, _diagnostics = parser.feed(
            "VIDEO_ENCODER_EXPORT_"
        )
        second_events, _diagnostics = parser.feed(
            'EVENT {"stage":"video",'
            '"step":1,"total":4}\n'
        )

        self.assertEqual(first_events, [])
        self.assertEqual(
            second_events,
            [
                {
                    "stage": "video",
                    "step": 1,
                    "total": 4
                }
            ]
        )

    def test_keeps_other_output_as_diagnostics(self):
        parser = ExportEventParser()

        events, diagnostics = parser.feed(
            "ordinary command output\n"
        )

        self.assertEqual(events, [])
        self.assertEqual(
            diagnostics,
            ["ordinary command output"]
        )


if __name__ == "__main__":
    unittest.main()
