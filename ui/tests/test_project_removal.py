import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.trim_export_queue_client import TrimExportQueueClient, TrimExportQueueError


class ProjectRemovalClientTest(unittest.TestCase):
    def test_preview_and_confirmation_are_separate_and_preserve_literal_paths(self):
        plan = {'format': 'video_encoder.project_removal', 'version': 1,
                'files': ['/Film & suite.json'], 'token': 'digest'}
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps(plan), stderr=''))
        client = TrimExportQueueClient(executable='/encoder', runner=runner)
        self.assertEqual(plan, client.remove_project_files('/Film & suite.json'))
        self.assertEqual(['/encoder', 'remove-project', '/Film & suite.json'], runner.call_args.args[0])
        runner.return_value.stdout = json.dumps('/recovery')
        self.assertEqual('/recovery', client.remove_project_files('/Film & suite.json', dependencies=True, token='digest'))
        self.assertEqual(['/encoder', 'remove-project', '/Film & suite.json', '--dependencies', '--confirm', 'digest'],
                         runner.call_args.args[0])

    def test_invalid_previews_are_rejected(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout='[]', stderr=''))
        client = TrimExportQueueClient(executable='/encoder', runner=runner)
        with self.assertRaises(TrimExportQueueError):
            client.remove_project_files('/film.json')
