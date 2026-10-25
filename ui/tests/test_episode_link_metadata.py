import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from video_encoder_ui.vidb_project_link import VidbProjectLink


class EpisodeLinkMetadataTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = Path(self.temp.name) / 'vidb.json'
        self.config.write_text(json.dumps({'url': 'https://vidb.test', 'token': 'a' * 64}), encoding='utf-8')
        self.project_id = '4d013c0a-7b54-4a67-aef2-7e1af7f6d410'

    def test_transmits_a_provisional_language_without_sending_the_inspection(self):
        transport = Mock(return_value={'status': 'unmatched', 'review_url': 'https://vidb.test/encoder_projects/episode'})
        link = VidbProjectLink(self.config, transport=transport)
        document = {'version': 2, 'project_id': self.project_id, 'sources': [
            {'path': '/commun/source.m2t', 'inspection': {'audio_tracks': [{'language': 'und'}]}}]}
        link.identify(document, Path('/videos/montage.json'), refresh=True)
        payload = transport.call_args.args[1]['project']
        self.assertEqual('VF', payload['language_hint'])
        self.assertNotIn('inspection', payload)
        self.assertEqual(['/commun/source.m2t'], payload['source_paths'])

    def test_keeps_a_same_origin_link_for_completing_an_existing_episode(self):
        response = {'status': 'identified', 'binding': {'project_id': self.project_id, 'record_id': 123,
                                                      'binding_token': 'signed'},
                    'review_url': 'https://vidb.test/encoder_projects/episode?request_token=signed'}
        result = VidbProjectLink.checked_response({'url': 'https://vidb.test'}, response, self.project_id)
        self.assertEqual(response['review_url'], result['review_url'])

    def test_does_not_accept_a_completion_link_to_another_server(self):
        response = {'status': 'identified', 'binding': {'project_id': self.project_id, 'record_id': 123,
                                                      'binding_token': 'signed'},
                    'review_url': 'https://other.test/episode'}
        with self.assertRaises(ValueError):
            VidbProjectLink.checked_response({'url': 'https://vidb.test'}, response, self.project_id)
