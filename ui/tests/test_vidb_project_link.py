import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.vidb_project_link import VidbProjectLink, NoRedirect
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter
from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader


class VidbProjectLinkTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.config = Path(self.directory.name) / "vidb.json"
        self.config.write_text(json.dumps({"url": "https://vidb.test", "token": "a" * 64}))
        self.project_id = str(uuid.uuid4())
        self.document = {"format": "video_encoder.trim_project", "version": 2,
                         "project_id": self.project_id,
                         "sources": [{"id": "source", "path": "/commun/capture.m2t"}], "timeline": []}

    def client(self, response=None, error=None):
        transport = Mock(return_value=response, side_effect=error)
        return VidbProjectLink(config_path=self.config, transport=transport), transport

    def test_planned_project_does_not_send_any_availability_or_viewing_flag(self):
        binding = {"project_id": self.project_id, "record_id": 123, "binding_token": "signed"}
        client, transport = self.client({"status": "identified", "binding": binding})
        result = client.identify(self.document, "/videos/Films/Film.json")
        self.assertEqual(result["record_id"], 123)
        payload = transport.call_args.args[1]["project"]
        self.assertEqual(set(payload), {"project_id", "project_path", "output_path", "source_paths"})
        self.assertEqual(payload["output_path"], "/videos/Films/Film.mkv")

    def test_confirmed_identity_survives_project_relocation_without_network(self):
        self.document["vidb"] = {"status": "identified", "project_id": self.project_id,
                                 "record_id": 123, "binding_token": "signed"}
        client, transport = self.client()
        result = client.identify(self.document, "/videos/Films/Autre dossier/Film.json")
        self.assertEqual(result["record_id"], 123)
        transport.assert_not_called()

    def test_unavailable_vidb_leaves_a_pending_request_without_losing_the_project(self):
        client, _ = self.client(error=TimeoutError("offline"))
        self.assertEqual(client.identify(self.document, "/videos/Film.json")["status"], "pending")
        self.assertEqual(self.document["project_id"], self.project_id)

    def test_review_link_must_stay_on_the_configured_vidb_origin(self):
        client, _ = self.client({"status": "needs_review", "review_url": "https://evil.test/"})
        self.assertEqual(client.identify(self.document, "/videos/Film.json")["status"], "pending")

    def test_wrong_project_binding_and_invalid_response_are_ignored(self):
        responses = [[], {"status": "identified", "binding": {"project_id": str(uuid.uuid4()),
                                                                "record_id": 123, "binding_token": "signed"}}]
        for response in responses:
            client, _ = self.client(response)
            self.assertEqual(client.identify(self.document, "/videos/Film.json")["status"], "pending")

    def test_no_configuration_or_nonlibrary_destination_never_contacts_production(self):
        client, transport = self.client()
        self.assertEqual(client.identify(self.document, "/tmp/Film.json")["status"], "disabled")
        self.config.unlink()
        self.assertEqual(client.identify(self.document, "/videos/Film.json")["status"], "disabled")
        transport.assert_not_called()

    def test_authentication_is_not_forwarded_to_redirects(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://elsewhere.test"))

    def test_writer_and_reader_preserve_uuid_and_binding_across_saves(self):
        document = {"format": "video_encoder.trim_project", "version": 2,
                    "sources": [{"id": "source", "path": "/commun/capture.m2t"}], "timeline": []}
        bridge = Mock()
        bridge.convert.side_effect = lambda session: document
        session = SimpleNamespace(analysis_workspaces=[], project_id=self.project_id, vidb={})
        link = Mock()
        link.identify.return_value = {"status": "identified", "project_id": self.project_id,
                                      "record_id": 123, "binding_token": "signed"}
        writer = TrimProjectFileWriter(bridge, vidb_link=link)
        first = Path(self.directory.name) / "Film.json"
        writer.save(session, first)
        loaded = TrimProjectFileReader().load(first)
        self.assertEqual(loaded.project_id, self.project_id)
        self.assertEqual(loaded.vidb["record_id"], 123)
        second = Path(self.directory.name) / "Film déplacé.json"
        writer.save(loaded, second)
        self.assertEqual(json.loads(second.read_text())["project_id"], self.project_id)
        self.assertNotIn("project_id", document)

    def test_a_new_session_gets_a_different_project_identity(self):
        first = VidbProjectLink.project_id(SimpleNamespace(project_id=None))
        second = VidbProjectLink.project_id(SimpleNamespace(project_id=None))
        self.assertNotEqual(first, second)
        self.assertEqual(uuid.UUID(first).version, 4)
