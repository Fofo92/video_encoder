import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.trim_export_queue_client import TrimExportQueueClient, TrimExportQueueError


class ProjectTrashClientTest(unittest.TestCase):
    def test_commands_keep_paths_and_tokens_as_separate_arguments(self):
        document = dict(format='video_encoder.project_trash', version=1, entries=[], errors=[])
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout=json.dumps(document), stderr=''))
        client = TrimExportQueueClient(executable='/encoder', runner=runner)
        self.assertEqual(document, client.project_trash())
        self.assertEqual(['/encoder', 'project-trash', 'list'], runner.call_args.args[0])
        runner.return_value.stdout = json.dumps('/Films & séries/.video_encoder_trash/id')
        client.project_trash('restore', '/Films & séries/.video_encoder_trash/id', 'token')
        self.assertEqual(['/encoder', 'project-trash', 'restore', '/Films & séries/.video_encoder_trash/id', 'token'],
                         runner.call_args.args[0])

    def test_invalid_listing_fails_without_inventing_an_empty_trash(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout='{}', stderr=''))
        client = TrimExportQueueClient(executable='/encoder', runner=runner)
        with self.assertRaises(TrimExportQueueError):
            client.project_trash()
