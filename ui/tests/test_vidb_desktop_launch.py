import json
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode
from urllib.error import HTTPError

from video_encoder_ui.desktop_launch import open_from_vidb
from video_encoder_ui.vidb_launch_client import LaunchError, checked_context, parse_launch_url, request_launch
from video_encoder_ui.vidb_project_link import VidbProjectLink


PROJECT = "b473298a-6ef6-4a94-9be0-8d177b681b9a"
CONTEXT = {"project_id": PROJECT, "record_id": 42, "record_title": "Film de test"}
CONFIG = {"url": "https://vidb.test", "token": "a" * 64}
URL = "vidb-encoder://prepare?" + urlencode({"ticket": "signed-ticket", "origin": CONFIG["url"]})


class VidbDesktopLaunchTest(unittest.TestCase):
    def test_a_copy_launch_dispatches_to_version_preparation_without_opening_a_montage(self):
        context = {**CONTEXT, "source_copy": {"id": 9, "path": "/videos/Monstres gentils.mkv"}}
        controller = SimpleNamespace(editor_window=None, open=Mock())
        callback = Mock(return_value=True)
        select = Mock()
        report = Mock()
        self.assertTrue(open_from_vidb(URL, link=Mock(configuration=Mock(return_value=CONFIG)),
                                       editor_controller=controller, select_source=select, report=report,
                                       transport=Mock(return_value=context), change_version=callback))
        callback.assert_called_once_with(source=context["source_copy"]["path"], context=context, ticket="signed-ticket")
        select.assert_not_called()
        controller.open.assert_not_called()
        report.assert_not_called()

    def test_an_old_or_cancelled_desktop_never_falls_back_to_a_new_montage_for_a_copy(self):
        context = {**CONTEXT, "source_copy": {"id": 9, "path": "/videos/Film.mkv"}}
        for callback in (None, Mock(return_value=False)):
            controller = SimpleNamespace(editor_window=None, open=Mock())
            select = Mock()
            result = open_from_vidb(URL, link=Mock(configuration=Mock(return_value=CONFIG)),
                                    editor_controller=controller, select_source=select, report=Mock(),
                                    transport=Mock(return_value=context), change_version=callback)
            self.assertFalse(result)
            controller.open.assert_not_called()
            select.assert_not_called()

    def test_a_second_click_returns_to_the_same_montage_without_replacing_its_source(self):
        editor = SimpleNamespace(trim_session=SimpleNamespace(project_id=PROJECT),
                                 show=Mock(), raise_=Mock(), activateWindow=Mock())
        controller = SimpleNamespace(editor_window=editor, open=Mock())
        select = Mock()
        result = open_from_vidb(URL, link=Mock(configuration=Mock(return_value=CONFIG)),
                                editor_controller=controller, select_source=select,
                                report=Mock(), transport=Mock(return_value=CONTEXT))
        self.assertTrue(result)
        controller.open.assert_not_called()
        select.assert_not_called()
        editor.activateWindow.assert_called_once()

    def test_ticket_is_only_accepted_for_the_configured_origin(self):
        self.assertEqual("signed-ticket", parse_launch_url(URL, CONFIG["url"]))
        for url in (URL.replace("vidb.test", "other.test"), URL + "&ticket=duplicate", URL + "#fragment",
                    URL.replace("prepare?", "other?"), URL.replace("vidb-encoder:", "https:"), URL + "\n"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_launch_url(url, CONFIG["url"])

    def test_invalid_context_cannot_select_a_project_or_a_record(self):
        for changes in ({"project_id": "other"}, {"record_id": True}, {"record_id": -1}, {"record_title": None}):
            with self.subTest(changes=changes), self.assertRaises(LaunchError):
                checked_context({**CONTEXT, **changes})

    def test_no_editor_is_opened_if_source_selection_is_cancelled(self):
        controller = SimpleNamespace(editor_window=None, open=Mock())
        result = open_from_vidb(URL, link=Mock(configuration=Mock(return_value=CONFIG)),
                                editor_controller=controller, select_source=Mock(return_value=None),
                                report=Mock(), transport=Mock(return_value=CONTEXT))
        self.assertFalse(result)
        controller.open.assert_not_called()

    def test_a_source_opens_with_the_expected_record_pending_and_never_queues_an_export(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.m2t"
            source.write_bytes(b"video")
            editor = SimpleNamespace(trim_session=SimpleNamespace(), set_project_modified=Mock(), statusBar=Mock())
            controller = SimpleNamespace(editor_window=None)
            controller.open = Mock(side_effect=lambda _path: setattr(controller, "editor_window", editor))
            transport = Mock(return_value=CONTEXT)
            report = Mock()
            result = open_from_vidb(URL, link=Mock(configuration=Mock(return_value=CONFIG)),
                                    editor_controller=controller, select_source=Mock(return_value=source),
                                    report=report, transport=transport)
        self.assertTrue(result)
        self.assertEqual(PROJECT, editor.trim_session.project_id)
        self.assertEqual("signed-ticket", editor.trim_session.vidb_launch)
        editor.set_project_modified.assert_called_once_with(True)
        transport.assert_called_once_with(CONFIG, "signed-ticket")
        report.assert_not_called()

    def test_refusing_to_close_the_previous_editor_preserves_its_state(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.m2t"
            source.write_bytes(b"video")
            previous = SimpleNamespace(trim_session=SimpleNamespace(project_id="existing"))
            controller = SimpleNamespace(editor_window=previous, open=Mock())
            result = open_from_vidb(URL, link=Mock(configuration=Mock(return_value=CONFIG)),
                                    editor_controller=controller, select_source=Mock(return_value=source),
                                    report=Mock(), transport=Mock(return_value=CONTEXT))
        self.assertFalse(result)
        self.assertEqual("existing", previous.trim_session.project_id)

    def test_a_project_file_cannot_be_silently_reassociated_as_a_new_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "project.json"
            source.write_text("{}")
            controller = SimpleNamespace(editor_window=None, open=Mock())
            report = Mock()
            result = open_from_vidb(URL, link=Mock(configuration=Mock(return_value=CONFIG)),
                                    editor_controller=controller, select_source=Mock(return_value=source),
                                    report=report, transport=Mock(return_value=CONTEXT))
        self.assertFalse(result)
        report.assert_called_once()
        controller.open.assert_not_called()

    def test_request_uses_only_the_configured_https_bridge_and_filters_its_token_parameter(self):
        response = Mock()
        response.read.return_value = json.dumps(CONTEXT).encode()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        with patch("video_encoder_ui.vidb_launch_client.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(CONTEXT, request_launch(CONFIG, "ticket"))
        request = opener.return_value.open.call_args.args[0]
        self.assertEqual("https://vidb.test/encoder_projects/launch_binding", request.full_url)
        self.assertEqual({"launch_token": "ticket"}, json.loads(request.data))
        self.assertEqual("Bearer " + CONFIG["token"], request.get_header("Authorization"))

    def test_rejected_requests_have_a_readable_message_without_retrying_elsewhere(self):
        for content, expected in (('{"error":"Demande invalide"}'.encode(), "invalide"), (b"", "refusée")):
            error = HTTPError(CONFIG["url"], 422, "Unprocessable Content", {}, io.BytesIO(content))
            with self.subTest(content=content), patch("video_encoder_ui.vidb_launch_client.build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaisesRegex(LaunchError, expected):
                    request_launch(CONFIG, "ticket")
                opener.return_value.open.assert_called_once()


class VidbLaunchBindingTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        config = Path(self.directory.name) / "vidb.json"
        config.write_text(json.dumps(CONFIG))
        self.transport = Mock()
        self.link = VidbProjectLink(config, transport=self.transport)
        self.document = {"project_id": PROJECT, "version": 2, "vidb_launch": "ticket",
                         "sources": [{"path": "/commun/source.m2t", "inspection": {
                             "audio_tracks": [{"language": "fra"}], "subtitle_tracks": []}}]}

    def test_explicit_ticket_bypasses_automatic_title_matching(self):
        response = {"status": "identified", "binding": {"project_id": PROJECT, "record_id": 42,
                                                         "binding_token": "binding"}}
        with patch("video_encoder_ui.vidb_project_link.request_launch", return_value=response) as launch:
            result = self.link.identify(self.document, "/videos/source.json")
        self.assertEqual(42, result["record_id"])
        self.transport.assert_not_called()
        self.assertEqual("ticket", launch.call_args.args[1])

    def test_failed_explicit_binding_never_falls_back_to_automatic_identification(self):
        with patch("video_encoder_ui.vidb_project_link.request_launch", side_effect=LaunchError("Demande expirée")):
            result = self.link.identify(self.document, "/videos/source.json")
        self.assertEqual("pending", result["status"])
        self.transport.assert_not_called()

    def test_a_damaged_saved_launch_ticket_never_falls_back_to_title_matching(self):
        for ticket in (None, "", 42):
            self.document["vidb_launch"] = ticket
            with self.subTest(ticket=ticket):
                result = self.link.identify(self.document, "/videos/source.json")
                self.assertEqual("pending", result["status"])
        self.transport.assert_not_called()

    def test_a_later_explicit_record_change_is_not_overwritten_by_the_initial_ticket(self):
        binding = {"status": "identified", "project_id": PROJECT, "record_id": 99, "binding_token": "new"}
        self.document["vidb"] = binding
        with patch("video_encoder_ui.vidb_project_link.request_launch") as launch:
            self.assertEqual(binding, self.link.identify(self.document, "/videos/source.json"))
        launch.assert_not_called()
