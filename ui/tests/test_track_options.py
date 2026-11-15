import unittest
from unittest.mock import Mock

from video_encoder_ui.track_options import preferred_mode, track_capabilities, used_source_paths


def complete_tracks():
    return {"audio_tracks": [{"language": "fra"}, {"language": "qaa"}],
            "subtitle_tracks": [{"language": "fra", "hearing_impaired": False, "forced": False}]}


class TrackOptionsTest(unittest.TestCase):
    def document(self, inspection=None):
        return {"version": 2, "sources": [{"id": "one", "path": "/source.m2t", "inspection": inspection}],
                "timeline": [{"type": "segment", "source_id": "one", "start_frame": 0, "end_frame": 100}]}

    def test_vmst_is_preferred_when_all_required_tracks_are_present(self):
        options = track_capabilities(self.document(complete_tracks()))
        self.assertTrue(all(options[mode] for mode in ("french_only", "original_without_subtitles", "original_with_subtitles")))
        self.assertEqual("original_with_subtitles", preferred_mode(options))

    def test_forced_or_hearing_impaired_subtitles_do_not_make_vmst_available(self):
        for flag in ("forced", "hearing_impaired"):
            details = complete_tracks()
            details["subtitle_tracks"][0][flag] = True
            options = track_capabilities(self.document(details))
            self.assertFalse(options["original_with_subtitles"])
            self.assertEqual("original_without_subtitles", preferred_mode(options))

    def test_missing_original_audio_disables_both_multilingual_versions(self):
        details = complete_tracks()
        details["audio_tracks"].pop()
        options = track_capabilities(self.document(details))
        self.assertEqual("french_only", preferred_mode(options))
        self.assertFalse(options["original_with_subtitles"])
        self.assertFalse(options["original_without_subtitles"])

    def test_audiodescription_is_not_used_as_the_french_audio(self):
        details = complete_tracks()
        details["audio_tracks"][0]["visual_impaired"] = True
        self.assertIsNone(preferred_mode(track_capabilities(self.document(details))))

    def test_only_used_sources_are_probed_and_all_of_them_must_support_the_mode(self):
        document = self.document()
        document["sources"].append({"id": "unused", "path": "/unused.m2t"})
        inspector = Mock()
        inspector.inspect.return_value = {"inspection": complete_tracks()}
        self.assertTrue(track_capabilities(document, inspector)["original_with_subtitles"])
        inspector.inspect.assert_called_once_with("/source.m2t")
        document["timeline"].append({"type": "segment", "source_id": "unused", "start_frame": 0, "end_frame": 100})
        second = complete_tracks()
        second["subtitle_tracks"] = []
        inspector.inspect.side_effect = [{"inspection": complete_tracks()}, {"inspection": second}]
        self.assertFalse(track_capabilities(document, inspector)["original_with_subtitles"])

    def test_legacy_projects_and_repeated_source_paths(self):
        document = {"version": 1, "timeline": [{"source": "/capture.m2t"}, {"source": "/capture.m2t"}]}
        self.assertEqual(["/capture.m2t"], used_source_paths(document))
        inspector = Mock()
        inspector.inspect.return_value = {"inspection": complete_tracks()}
        self.assertTrue(track_capabilities(document, inspector)["original_with_subtitles"])
        inspector.inspect.assert_called_once_with("/capture.m2t")

    def test_absent_inspections_do_not_claim_track_availability(self):
        self.assertIsNone(track_capabilities(self.document()))
        self.assertIsNone(track_capabilities({"version": 2, "sources": [], "timeline": []}))


if __name__ == "__main__":
    unittest.main()
