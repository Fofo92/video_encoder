import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlencode

from video_encoder_ui import desktop_launch
from video_encoder_ui.vidb_launch_client import LaunchError, parse_desktop_url, request_launch


CONFIG = {"url": "https://vidb.test", "token": "a" * 64}
URL = "vidb-encoder://desktop?" + urlencode({"ticket": "signed", "origin": CONFIG["url"]})
ACTIONS = ("new_montage", "open_project", "encode_dvd", "show_queue", "change_version")


class VidbDesktopCommandsTest(unittest.TestCase):
    def dispatch(self, *, url=URL, transport=None, actions=None):
        self.report = Mock()
        self.controller = SimpleNamespace(editor_window=object(), open=Mock())
        self.select_source = Mock(side_effect=AssertionError("No record-specific source chooser expected"))
        return desktop_launch.dispatch_from_vidb(
            url, link=Mock(configuration=Mock(return_value=CONFIG)), editor_controller=self.controller,
            select_source=self.select_source, actions=actions or self.actions,
            report=self.report, transport=transport or self.transport)

    def setUp(self):
        self.actions = {action: Mock() for action in ACTIONS}
        self.transport = Mock()

    def test_each_menu_command_calls_only_the_existing_matching_desktop_action(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                for callback in self.actions.values():
                    callback.reset_mock()
                self.transport.return_value = {"desktop_action": action}
                self.assertTrue(self.dispatch())
                self.actions[action].assert_called_once_with()
                for other in set(ACTIONS) - {action}:
                    self.actions[other].assert_not_called()
                self.controller.open.assert_not_called()
                self.report.assert_not_called()
        self.transport.assert_called_with(CONFIG, "signed", desktop=True)

    def test_unknown_actions_never_fall_back_to_a_new_project_or_any_callback(self):
        self.transport.return_value = {"desktop_action": "run_command"}
        self.assertFalse(self.dispatch())
        for callback in self.actions.values():
            callback.assert_not_called()
        self.report.assert_called_once()

    def test_bridge_failure_and_callback_failure_are_reported_without_trying_another_action(self):
        self.transport.side_effect = LaunchError("Passerelle indisponible")
        self.assertFalse(self.dispatch())
        self.report.assert_called_once_with("Passerelle indisponible")
        self.transport.side_effect = None
        self.transport.return_value = {"desktop_action": "encode_dvd"}
        self.actions["encode_dvd"].side_effect = RuntimeError("Lecteur indisponible")
        self.assertFalse(self.dispatch())
        self.actions["new_montage"].assert_not_called()
        self.report.assert_called_once_with("Lecteur indisponible")

    def test_another_origin_or_extra_query_parameters_are_rejected_before_contacting_vidb(self):
        for url in (URL.replace("vidb.test", "other.test"), URL + "&command=anything",
                    URL.replace("desktop?", "unexpected?")):
            with self.subTest(url=url):
                self.transport.reset_mock()
                self.assertFalse(self.dispatch(url=url))
                self.transport.assert_not_called()

    def test_record_preparation_links_keep_their_existing_identification_flow(self):
        url = URL.replace("//desktop?", "//prepare?")
        with patch.object(desktop_launch, "open_from_vidb", return_value=True) as prepare:
            self.assertTrue(self.dispatch(url=url))
        prepare.assert_called_once()
        self.transport.assert_not_called()
        for callback in self.actions.values():
            callback.assert_not_called()

    def test_desktop_protocol_is_scoped_separately_from_record_preparation(self):
        self.assertEqual("signed", parse_desktop_url(URL, CONFIG["url"]))
        with self.assertRaises(LaunchError):
            parse_desktop_url(URL.replace("//desktop?", "//prepare?"), CONFIG["url"])

    def test_desktop_request_uses_its_own_filtered_token_and_cannot_associate_a_project(self):
        response = Mock()
        response.read.return_value = b'{"desktop_action":"open_project"}'
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        with patch("video_encoder_ui.vidb_launch_client.build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual({"desktop_action": "open_project"}, request_launch(CONFIG, "signed", desktop=True))
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual({"desktop_token": "signed"}, json.loads(request.data))
            opener.reset_mock()
            with self.assertRaises(LaunchError):
                request_launch(CONFIG, "signed", {"project_id": "any"}, desktop=True)
            opener.assert_not_called()
