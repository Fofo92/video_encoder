import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import PySide6
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import catalogue_destination as destination
from video_encoder_ui.vidb_project_link import VidbProjectLink
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter


class CatalogueDestinationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.config = self.root / "vidb.json"
        self.config.write_text(json.dumps({"url": "https://vidb.test", "token": "a" * 64}), encoding="utf-8")
        self.session = SimpleNamespace(sources=[SimpleNamespace(path=Path('/commun/to_be_cut/Adieu Philippine.m2t'))])
        self.proposed = Path('/videos/Adieu Philippine.mkv')

    def metadata(self, **changes):
        return {"french_title": "Adieu Philippine", "original_title": "", "year": 1962,
                "genres": ["Comédie", "Drame"], "countries": ["France"],
                "record_kind": "standalone_video", **changes}

    def test_proposes_the_combined_directory_for_both_film_genres(self):
        (self.root / 'Drame').mkdir()
        (self.root / 'Comédie, Drame').mkdir()
        result = destination.suggested_film_output(self.metadata(), self.proposed, self.root)
        self.assertEqual(self.root / 'Comédie, Drame' / 'Adieu Philippine.mkv', result)

    def test_a_single_genre_uses_its_own_directory(self):
        (self.root / 'Western').mkdir()
        result = destination.suggested_film_output(self.metadata(genres=['Western']), self.proposed, self.root)
        self.assertEqual(self.root / 'Western', result.parent)

    def test_genre_order_does_not_change_the_existing_directory(self):
        (self.root / 'Policier, Thriller').mkdir()
        result = destination.suggested_film_output(self.metadata(genres=['Thriller', 'Policier']), self.proposed, self.root)
        self.assertEqual(self.root / 'Policier, Thriller', result.parent)

    def test_directory_punctuation_and_accents_do_not_change_the_genre_identity(self):
        (self.root / 'Science-Fiction, Thriller').mkdir()
        result = destination.suggested_film_output(
            self.metadata(genres=['Science fiction', 'Thriller']), self.proposed, self.root)
        self.assertEqual(self.root / 'Science-Fiction, Thriller', result.parent)

    def test_no_genre_is_silently_dropped_when_the_combination_is_missing(self):
        (self.root / 'Drame').mkdir()
        result = destination.suggested_film_output(self.metadata(), self.proposed, self.root)
        self.assertEqual(self.proposed.parent, result.parent)

    def test_ambiguous_duplicate_combination_directories_require_manual_choice(self):
        (self.root / 'Comédie, Drame').mkdir()
        (self.root / 'Drame, Comédie').mkdir()
        result = destination.suggested_film_output(self.metadata(), self.proposed, self.root)
        self.assertEqual(self.proposed.parent, result.parent)

    def test_does_not_duplicate_an_identical_original_title(self):
        result = destination.suggested_film_output(self.metadata(original_title='Adieu Philippine'), self.proposed, self.root)
        self.assertEqual('Adieu Philippine.mkv', result.name)

    def test_keeps_a_distinct_original_title_and_never_uses_slashes_in_a_filename(self):
        result = destination.suggested_film_output(
            self.metadata(french_title='Titre / français', original_title='Original'), self.proposed, self.root)
        self.assertEqual('Titre _ français (Original).mkv', result.name)

    def test_external_genres_cannot_select_a_parent_directory(self):
        result = destination.suggested_film_output(self.metadata(genres=['..']), self.proposed, self.root)
        self.assertEqual(self.proposed.parent, result.parent)

    def test_identification_precedes_the_destination_dialog_and_reuses_the_session_uuid(self):
        def transport(_config, payload):
            project = payload['project']
            return {'status': 'identified', 'binding': {'project_id': project['project_id'],
                    'record_id': 123, 'binding_token': 'signed'}, 'metadata': self.metadata()}
        link = VidbProjectLink(self.config, transport=transport)
        writer = SimpleNamespace(vidb_link=link)
        with patch.object(destination, 'confirm_destination', return_value=self.proposed) as confirm:
            result = destination.prepare_catalogue_destination(
                None, self.session, self.session.sources[0].path, self.proposed, writer)
        self.assertEqual(self.proposed, result)
        self.assertEqual(123, self.session.vidb['record_id'])
        self.assertEqual(self.session.project_id, self.session.vidb['project_id'])
        self.assertEqual(1962, confirm.call_args.args[1]['year'])

    def test_missing_film_opens_creation_without_discarding_the_montage(self):
        transport = Mock(return_value={'status': 'unmatched', 'review_url': 'https://vidb.test/encoder_projects/catalogue'})
        writer = SimpleNamespace(vidb_link=VidbProjectLink(self.config, transport=transport))
        with patch.object(destination, 'review_before_destination', return_value=None):
            result = destination.prepare_catalogue_destination(
                None, self.session, self.session.sources[0].path, self.proposed, writer)
        self.assertIsNone(result)
        self.assertEqual(1, len(self.session.sources))
        self.assertTrue(self.session.project_id)

    def test_an_offline_refresh_never_discards_an_existing_valid_binding(self):
        self.session.project_id = '4d013c0a-7b54-4a67-aef2-7e1af7f6d410'
        binding = {'status': 'identified', 'project_id': self.session.project_id,
                   'record_id': 123, 'binding_token': 'signed'}
        document = {'project_id': self.session.project_id, 'vidb': binding, 'version': 2, 'sources': []}
        link = VidbProjectLink(self.config, transport=Mock(side_effect=OSError('offline')))
        self.assertEqual(binding, link.identify(document, self.proposed.with_suffix('.json'), refresh=True))

    def test_no_configuration_preserves_the_existing_save_workflow(self):
        writer = SimpleNamespace(vidb_link=VidbProjectLink(self.root / 'missing.json'))
        self.assertEqual(self.proposed, destination.prepare_catalogue_destination(
            None, self.session, self.session.sources[0].path, self.proposed, writer))

    def test_catalogue_metadata_is_displayed_in_memory_without_becoming_a_second_catalogue_in_project_json(self):
        result = {'status': 'identified', 'record_id': 123, 'binding_token': 'signed',
                  'project_id': '4d013c0a-7b54-4a67-aef2-7e1af7f6d410', 'metadata': self.metadata()}
        link = Mock()
        link.identify.return_value = result
        bridge = Mock()
        bridge.convert.return_value = {'format': 'video_encoder.trim_project', 'version': 2}
        session = SimpleNamespace(project_id=result['project_id'], vidb=result)
        writer = TrimProjectFileWriter(bridge, vidb_link=link)
        path = self.root / 'film.json'
        writer.save(session, path)
        saved = json.loads(path.read_text(encoding='utf-8'))
        self.assertEqual(123, saved['vidb']['record_id'])
        self.assertNotIn('metadata', saved['vidb'])
        self.assertEqual(1962, writer.vidb_result['metadata']['year'])
