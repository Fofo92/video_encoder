import tempfile
import unittest
from pathlib import Path

from video_encoder_ui.episode_destination import suggested_episode_output


class EpisodeDestinationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metadata = {'record_kind': 'episode', 'series_titles': ["Cat’s Eyes"],
                         'season_number': 2, 'episode_number': 1, 'french_title': 'Un nouvel espoir'}
        self.suggested = self.root / 'provisoire - valide.mkv'

    def test_uses_the_existing_directory_without_changing_its_old_counts(self):
        folder = self.root / '_incomplet' / "Cat's Eyes (I - 02_08)" / 'Saison 02'
        folder.mkdir(parents=True)
        self.assertEqual(folder / 'S02 E01 - Un nouvel espoir.mkv',
                         suggested_episode_output(self.metadata, self.suggested, self.root))

    def test_ambiguous_series_keep_the_manual_directory_but_use_the_canonical_name(self):
        for group in ('_complet', '_incomplet'):
            (self.root / group / "Cat's Eyes" / 'Saison 02').mkdir(parents=True)
        result = suggested_episode_output(self.metadata, self.suggested, self.root)
        self.assertEqual(self.suggested.parent, result.parent)
        self.assertEqual('S02 E01 - Un nouvel espoir.mkv', result.name)

    def test_a_missing_season_is_proposed_without_creating_it_yet(self):
        folder = self.root / "Cat's Eyes"
        folder.mkdir()
        result = suggested_episode_output(self.metadata, self.suggested, self.root)
        self.assertEqual(folder / "Saison 02", result.parent)
        self.assertFalse((folder / 'Saison 02').exists())

    def test_missing_numbers_keep_the_original_proposal(self):
        self.assertEqual(self.suggested, suggested_episode_output({}, self.suggested, self.root))

    def test_title_cannot_escape_the_season_directory(self):
        self.metadata['french_title'] = '../../Autre'
        result = suggested_episode_output(self.metadata, self.suggested, self.root)
        self.assertEqual(self.root, result.parent)
        self.assertNotIn('/', result.name)

    def test_an_episode_without_a_known_directory_defaults_to_series_root(self):
        self.metadata.update(french_title='Tous pour elle', original_title='It Takes a Village',
                             season_number=7, episode_number=1, series_titles=['Esprits criminels'])
        result = suggested_episode_output(self.metadata, Path('/videos/capture.mkv'), self.root)
        self.assertEqual(self.root / 'S07 E01 - Tous pour elle (It Takes a Village).mkv', result)

    def test_an_explicit_manual_directory_is_preserved(self):
        suggested = self.root / 'mon classement/capture.mkv'
        result = suggested_episode_output(self.metadata, suggested, self.root)
        self.assertEqual(suggested.parent, result.parent)
