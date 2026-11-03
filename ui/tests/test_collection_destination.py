import tempfile
import unittest
from pathlib import Path

try:
    import PySide6
except ModuleNotFoundError as error:
    if error.name != 'PySide6':
        raise
    raise unittest.SkipTest('PySide6 is unavailable') from error

from video_encoder_ui.catalogue_destination import suggested_film_output


class CollectionDestinationTest(unittest.TestCase):
    def test_film_is_placed_inside_its_collection_under_its_genres(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = {'french_title': 'Film', 'genres': ['Guerre', 'Histoire'],
                        'destination_container': {'record_kind': 'collection',
                                                  'french_title': 'Collection'}}
            result = suggested_film_output(metadata, '/videos/Film.json', film_root=root)
            self.assertEqual(root / 'Guerre, Histoire' / 'Collection' / 'Film.mkv', result)
            self.assertFalse(result.parent.exists())

    def test_documentary_directly_in_a_series_has_no_combined_genre_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = {'french_title': 'Le ciel', 'genres': ['Documentaire'],
                        'destination_container': {'record_kind': 'series',
                                                  'french_title': 'La science',
                                                  'original_title': 'La science', 'countries': ['France']}}
            result = suggested_film_output(metadata, '/videos/Film.json', documentary_root=root)
            self.assertEqual(root / 'La science' / 'Le ciel.mkv', result)

    def test_existing_collection_directory_with_year_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'Action' / 'Saga (2000)'
            folder.mkdir(parents=True)
            metadata = {'french_title': 'Film', 'genres': ['Action'],
                        'destination_container': {'record_kind': 'collection', 'french_title': 'Saga'}}
            self.assertEqual(folder / 'Film.mkv', suggested_film_output(metadata, '/videos/Film.json', root))

    def test_container_name_is_a_single_safe_path_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = {'french_title': 'Film', 'genres': ['Action'],
                        'destination_container': {'record_kind': 'collection', 'french_title': '../Saga/Films'}}
            result = suggested_film_output(metadata, '/videos/Film.json', root)
            self.assertEqual(root / 'Action' / '_Saga_Films' / 'Film.mkv', result)

    def test_foreign_collection_retains_both_titles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata = {'french_title': 'Film', 'genres': ['Action'],
                        'destination_container': {'record_kind': 'collection', 'french_title': 'Saga',
                                                  'original_title': 'Original', 'countries': ['Royaume-Uni']}}
            result = suggested_film_output(metadata, '/videos/Film.json', root)
            self.assertEqual(root / 'Action' / 'Saga (Original)' / 'Film.mkv', result)
