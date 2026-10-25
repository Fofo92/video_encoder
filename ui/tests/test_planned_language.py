import unittest

from video_encoder_ui.planned_language import planned_language


class PlannedLanguageTest(unittest.TestCase):
    def document(self, tracks):
        return {"sources": [{"inspection": {"audio_tracks": tracks}}]}

    def test_a_single_french_or_unknown_track_proposes_vf(self):
        for language in ("fra", "fre", "fr", "und", None):
            self.assertEqual("VF", planned_language(self.document([{"language": language}])))

    def test_multilingual_and_english_sources_need_review_before_export(self):
        self.assertIsNone(planned_language(self.document([{"language": "fra"}, {"language": "eng"}])))
        self.assertIsNone(planned_language(self.document([{"language": "eng"}])))

    def test_no_guess_when_inspection_is_missing_or_audio_is_descriptive(self):
        self.assertIsNone(planned_language({}))
        self.assertIsNone(planned_language({"sources": [{"inspection": None}]}))
        self.assertIsNone(planned_language(self.document([{"language": "fra", "visual_impaired": True}])))

    def test_every_source_must_support_the_same_proposal(self):
        document = self.document([{"language": "fra"}])
        document["sources"].append({"inspection": {"audio_tracks": [{"language": "eng"}]}})
        self.assertIsNone(planned_language(document))
