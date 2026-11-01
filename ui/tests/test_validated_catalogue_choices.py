import unittest
from pathlib import Path
from unittest.mock import patch

from video_encoder_ui.episode_destination import suggested_episode_output
from video_encoder_ui.original_language_review import proposed_mode
from video_encoder_ui.title_convention import title_with_original


class ValidatedCatalogueChoicesTest(unittest.TestCase):
    def test_french_coproduction_uses_only_the_french_title_even_when_titles_differ(self):
        self.assertEqual('Le départ', title_with_original({
            'french_title': 'Le départ', 'original_title': 'Departure', 'countries': ['Belgique', 'France']}))

    def test_foreign_identical_titles_remain_bilingual(self):
        self.assertEqual('Boston (Boston)', title_with_original({
            'french_title': 'Boston', 'original_title': 'Boston', 'countries': ['États-Unis']}))

    def test_documentary_series_uses_documentary_root_and_series_countries(self):
        metadata = {'season_number': 1, 'episode_number': 1, 'series_year': 2023,
                    'series_french_title': 'La vérité sur les envahisseurs',
                    'series_original_title': 'La vérité sur les envahisseurs',
                    'series_titles': ['La vérité sur les envahisseurs'],
                    'series_genres': ['Documentaire'], 'series_countries': ['France'],
                    'countries': ['France'], 'french_title': 'Des animaux et des plantes nuisibles ?',
                    'original_title': 'Des animaux et des plantes nuisibles ?'}
        with patch('video_encoder_ui.episode_destination.series_directories', return_value=[]):
            result = suggested_episode_output(metadata, Path('/videos/capture.mkv'))
        self.assertEqual(Path('/videos/Documentaires/La vérité sur les envahisseurs (2023)/Saison 01/'
                              'S01 E01 - Des animaux et des plantes nuisibles ?.mkv'), result)

    def test_explicit_documentary_destination_is_preserved(self):
        metadata = {'season_number': 1, 'episode_number': 2, 'french_title': 'Épisode',
                    'series_genres': ['Documentaire']}
        with patch('video_encoder_ui.episode_destination.series_directories', return_value=[]):
            result = suggested_episode_output(metadata, Path('/mon/classement/capture.mkv'))
        self.assertEqual(Path('/mon/classement'), result.parent)

    def test_validated_language_version_wins_over_external_original_language(self):
        for version, expected in [('VF', 'french_only'), ('VM', 'original_without_subtitles'),
                                  ('VMST', 'original_with_subtitles')]:
            with self.subTest(version=version):
                result = {'status': 'identified', 'metadata': {'language_version': version,
                          'original_language_evidence': {'provider': 'tmdb', 'status': 'foreign', 'language': 'en'}}}
                self.assertEqual(expected, proposed_mode(result))

    def test_undetermined_version_still_uses_external_evidence(self):
        result = {'status': 'identified', 'metadata': {'language_version': 'IND',
                  'original_language_evidence': {'provider': 'tmdb', 'status': 'french', 'language': 'fr'}}}
        self.assertEqual('french_only', proposed_mode(result))
