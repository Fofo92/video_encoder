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

    def client(self, response=None, error=None, inspector=None):
        transport = Mock(return_value=response, side_effect=error)
        return VidbProjectLink(config_path=self.config, transport=transport, inspector=inspector), transport

    def test_planned_project_does_not_send_any_availability_or_viewing_flag(self):
        binding = {"project_id": self.project_id, "record_id": 123, "binding_token": "signed"}
        client, transport = self.client({"status": "identified", "binding": binding})
        result = client.identify(self.document, "/videos/Films/Film.json")
        self.assertEqual(result["record_id"], 123)
        payload = transport.call_args.args[1]["project"]
        self.assertEqual(set(payload), {"project_id", "project_path", "output_path", "source_paths"})
        self.assertEqual(payload["output_path"], "/videos/Films/Film.mkv")

    def montage(self):
        self.document["timeline"] = [
            {"type": "segment", "source_id": "source", "start_frame": 0, "end_frame": 100}]

    def inspector(self, subtitles=True):
        inspector = Mock()
        inspector.inspect.return_value = {"inspection": {
            "audio_tracks": [{"language": "fre"}, {"language": "qaa"}],
            "subtitle_tracks": [{"language": "fra", "hearing_impaired": False}] if subtitles else []}}
        return inspector

    def test_initial_review_contains_vmst_hint_even_before_the_project_has_cached_inspections(self):
        self.montage()
        inspector = self.inspector()
        client, transport = self.client(
            {"status": "needs_review", "review_url": "https://vidb.test/encoder_projects/episode"},
            inspector=inspector)
        result = client.identify(self.document, "/videos/Film.json")
        self.assertEqual('needs_review', result['status'])
        self.assertEqual('VMST', transport.call_args.args[1]['project']['language_hint'])
        inspector.inspect.assert_called_once_with('/commun/capture.m2t')
        self.assertNotIn('inspection', self.document['sources'][0])

    def test_real_provisional_path_only_context_is_inspected_before_the_first_review(self):
        from video_encoder_ui.vidb_project_context import project_identification_context
        source = Path('/commun/to_be_cut/Adieu Philippine.m2t')
        session = SimpleNamespace(sources=[SimpleNamespace(path=source)])
        document, path = project_identification_context(session, source, Path('/videos/Film.mkv'))
        self.assertNotIn('timeline', document)
        self.assertNotIn('id', document['sources'][0])
        inspector = self.inspector()
        client, transport = self.client(
            {"status": "needs_review", "review_url": "https://vidb.test/encoder_projects/episode"},
            inspector=inspector)
        result = client.identify(document, path, refresh=True)
        self.assertEqual('needs_review', result['status'])
        self.assertEqual('VMST', transport.call_args.args[1]['project']['language_hint'])
        inspector.inspect.assert_called_once_with(str(source))
        self.assertNotIn('timeline', document)

    def test_sources_without_subtitles_propose_vm_when_both_audio_tracks_exist(self):
        self.montage()
        client, transport = self.client(
            {"status": "needs_review", "review_url": "https://vidb.test/encoder_projects/episode"},
            inspector=self.inspector(subtitles=False))
        client.identify(self.document, "/videos/Film.json")
        self.assertEqual('VM', transport.call_args.args[1]['project']['language_hint'])

    def test_a_scoped_explicit_vf_selection_is_sent_unchanged_without_probing(self):
        from video_encoder_ui.original_language_review import selection_scope
        self.montage()
        self.document['track_selection'] = {
            'mode': 'french_only', 'confirmed_by': 'user', 'scope': selection_scope(self.document)}
        inspector = Mock()
        client, transport = self.client(
            {"status": "needs_review", "review_url": "https://vidb.test/encoder_projects/episode"},
            inspector=inspector)
        client.identify(self.document, "/videos/Film.json")
        self.assertEqual('VF', transport.call_args.args[1]['project']['language_hint'])
        inspector.inspect.assert_not_called()

    def test_inspection_failure_is_reported_instead_of_sending_a_form_without_track_information(self):
        from video_encoder_ui.media_inspection_client import MediaInspectionError
        self.montage()
        inspector = Mock()
        inspector.inspect.side_effect = MediaInspectionError('source unreadable')
        client, transport = self.client(inspector=inspector)
        result = client.identify(self.document, "/videos/Film.json")
        self.assertEqual('pending', result['status'])
        self.assertIn('Inspection des pistes', result['reason'])
        transport.assert_not_called()

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
