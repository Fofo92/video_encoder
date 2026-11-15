import unittest

from video_encoder_ui.planned_language import planned_language
from video_encoder_ui.original_language_review import selection_scope


class PlannedLanguageTest(unittest.TestCase):
    def document(self, tracks):
        return {"sources": [{"inspection": {"audio_tracks": tracks}}]}

    def test_a_single_french_or_unknown_track_proposes_vf(self):
        for language in ("fra", "fre", "fr", "und", None):
            self.assertEqual("VF", planned_language(self.document([{"language": language}])))

    def test_multilingual_and_english_sources_need_review_before_export(self):
        self.assertIsNone(planned_language(self.document([{"language": "fra"}, {"language": "eng"}])))
        self.assertIsNone(planned_language(self.document([{"language": "eng"}])))

    def test_vmst_is_the_hint_when_french_original_and_ordinary_french_subtitles_are_present(self):
        document = self.document([{"language": "fra"}, {"language": "qaa"}])
        document["sources"][0]["inspection"]["subtitle_tracks"] = [{"language": "fra"}]
        self.assertEqual("VMST", planned_language(document))
        document["sources"][0]["inspection"]["subtitle_tracks"][0]["hearing_impaired"] = True
        self.assertIsNone(planned_language(document))

    def test_an_explicit_scoped_choice_remains_authoritative_over_the_source_hint(self):
        document = {"version": 2, "project_id": "project", "vidb": {"record_id": 42},
                    "sources": [{"id": "source", "path": "/source.m2t"}], "timeline": []}
        document["track_selection"] = {"mode": "french_only", "scope": selection_scope(document)}
        self.assertEqual("VF", planned_language(document))
        document["track_selection"]["scope"]["record_id"] = 43
        self.assertIsNone(planned_language(document))

    def test_no_guess_when_inspection_is_missing_or_audio_is_descriptive(self):
        self.assertIsNone(planned_language({}))
        self.assertIsNone(planned_language({"sources": [{"inspection": None}]}))
        self.assertIsNone(planned_language(self.document([{"language": "fra", "visual_impaired": True}])))

    def test_every_source_must_support_the_same_proposal(self):
        document = self.document([{"language": "fra"}])
        document["sources"].append({"inspection": {"audio_tracks": [{"language": "eng"}]}})
        self.assertIsNone(planned_language(document))
