import unittest

from video_encoder_ui.audio_preflight_summary import audio_preflight_summary


def check(source="/commun/to_be_cut/Friends.m2t", index=1, language="fra", status="signal_detected"):
    return {"source": source, "track_index": index, "language": language, "analysis": {"status": status}}


class AudioPreflightSummaryTest(unittest.TestCase):
    def test_shared_destination_is_not_repeated_for_project_and_video(self):
        text, details = audio_preflight_summary({"audio_checks": []}, "/videos/Films/Un film.mkv")
        self.assertEqual(1, text.count("/videos/Films"))
        self.assertEqual(1, text.count("Un film"))
        self.assertIn("projet <b>.json</b>", text)
        self.assertIn("vidéo <b>.mkv</b>", text)
        self.assertIn("/videos/Films/Un film.json", details)
        self.assertIn("/videos/Films/Un film.mkv", details)

    def test_tracks_from_the_same_source_are_grouped(self):
        report = {"audio_checks": [check(), check(index=2, language="qaa")]}
        text, details = audio_preflight_summary(report, "/videos/Friends.mkv")
        self.assertEqual(1, text.count("<b>Friends.m2t</b>"))
        self.assertIn("Piste 1 · fra — signal détecté", text)
        self.assertIn("Piste 2 · qaa — signal détecté", text)
        self.assertEqual(1, details.count("/commun/to_be_cut/Friends.m2t"))

    def test_multiple_sources_remain_distinct_even_with_the_same_filename(self):
        report = {"audio_checks": [check("/commun/one/source.m2t"), check("/commun/two/source.m2t")]}
        text, details = audio_preflight_summary(report, "/videos/Film.mkv")
        self.assertIn("<b>/commun/one/source.m2t</b>", text)
        self.assertIn("<b>/commun/two/source.m2t</b>", text)
        self.assertIn("/commun/one/source.m2t", details)
        self.assertIn("/commun/two/source.m2t", details)

    def test_inconclusive_status_and_unspecified_language_remain_explicit(self):
        report = {"audio_checks": [check(language=None, status="inconclusive")]}
        text, _ = audio_preflight_summary(report, "/videos/Film.mkv")
        self.assertIn("non précisée", text)
        self.assertIn("<b>résultat non concluant</b>", text)
        self.assertIn("pas la langue", text)
        self.assertIn("<b>Annuler</b> conserve le montage.", text)

    def test_paths_language_and_unknown_status_cannot_be_interpreted_as_html(self):
        report = {"audio_checks": [check("/commun/<film>&.m2t", language="<fra>", status="<status>")]}
        text, details = audio_preflight_summary(report, "/videos/<titre>&.mkv")
        for raw in ("<film>", "<titre>", "<fra>", "<status>"):
            self.assertNotIn(raw, text)
        self.assertIn("&lt;titre&gt;&amp;", text)
        self.assertIn("&lt;fra&gt;", text)
        self.assertIn("/videos/<titre>&.mkv", details)

    def test_empty_checks_are_explained(self):
        text, _ = audio_preflight_summary({"audio_checks": []}, "/videos/Film.mkv")
        self.assertIn("Aucune piste audio à contrôler.", text)


if __name__ == "__main__":
    unittest.main()
