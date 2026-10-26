import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from video_encoder_ui import catalogue_destination as destination
except ModuleNotFoundError as error:
    if error.name != 'PySide6':
        raise
    raise unittest.SkipTest('PySide6 is unavailable') from error


class EpisodeManualDestinationTest(unittest.TestCase):
    def test_manual_choice_keeps_the_canonical_episode_name_and_series_root(self):
        metadata = {'record_kind': 'episode', 'french_title': 'Tous pour elle',
                    'original_title': 'It Takes a Village', 'countries': ['États-Unis'],
                    'season_number': 7, 'episode_number': 1, 'series_titles': ['Esprits criminels']}
        dialog = Mock()
        buttons = [Mock(), Mock(), Mock()]
        dialog.addButton.side_effect = buttons
        dialog.clickedButton.return_value = buttons[1]
        with patch.object(destination.QtWidgets, 'QMessageBox', return_value=dialog), \
             patch('video_encoder_ui.episode_destination.series_directory', return_value=None):
            result = destination.confirm_episode_destination(
                None, metadata, Path('/videos/Esprits criminels - S07 E01 Tous pour elle.mkv'))
        self.assertEqual(Path('/videos/Séries TV/S07 E01 - Tous pour elle (It Takes a Village).mkv'), result)

    def test_identical_foreign_titles_remain_repeated_in_the_episode_name(self):
        metadata = {'french_title': 'Village', 'original_title': 'Village', 'countries': ['États-Unis'],
                    'season_number': 7, 'episode_number': 1}
        with patch('video_encoder_ui.episode_destination.series_directory', return_value=None):
            result = destination.suggested_episode_output(metadata, Path('/videos/capture.mkv'))
        self.assertEqual('S07 E01 - Village (Village).mkv', result.name)
