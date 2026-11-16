import time
import unittest
import uuid
from unittest.mock import Mock, patch

try:
    from PySide6 import QtNetwork, QtWidgets
except ModuleNotFoundError as error:
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui.desktop_inbox import DesktopInbox, start_inbox


class DesktopInboxTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.inbox = DesktopInbox(name="video-encoder-test-" + uuid.uuid4().hex)
        self.addCleanup(self.inbox.close)

    def pump_until(self, condition):
        deadline = time.monotonic() + 2
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
        self.assertTrue(condition(), "La livraison locale n’a pas abouti dans le délai du test")

    def test_a_browser_launch_is_delivered_once_to_the_existing_application(self):
        received = Mock()
        self.inbox.set_handler(received)
        client = QtNetwork.QLocalSocket()
        self.addCleanup(client.abort)
        client.connectToServer(self.inbox.name)
        self.assertTrue(client.waitForConnected(500))
        client.write(b"vidb-encoder://prepare?ticket=test\n")
        client.flush()
        self.pump_until(lambda: received.call_count == 1)
        self.pump_until(lambda: client.bytesAvailable() > 0)
        self.assertEqual(b"queued", bytes(client.readAll()).strip())
        received.assert_called_once_with("vidb-encoder://prepare?ticket=test")

    def test_nested_event_processing_does_not_open_two_source_dialogs(self):
        sequence = []

        def handler(url):
            sequence.append(("start", url))
            if url.endswith("one"):
                self.inbox.submit("vidb-encoder://two")
                self.app.processEvents()
            sequence.append(("end", url))

        self.inbox.set_handler(handler)
        self.inbox.submit("vidb-encoder://one")
        self.pump_until(lambda: len(sequence) == 4)
        self.assertEqual([("start", "vidb-encoder://one"), ("end", "vidb-encoder://one"),
                          ("start", "vidb-encoder://two"), ("end", "vidb-encoder://two")], sequence)

    def test_normal_second_instance_does_not_create_a_second_inbox(self):
        with self.assertRaises(OSError):
            DesktopInbox(name=self.inbox.name)
        self.assertTrue(self.inbox.server.isListening())
        client = QtNetwork.QLocalSocket()
        self.addCleanup(client.abort)
        client.connectToServer(self.inbox.name)
        self.assertTrue(client.waitForConnected(500))

    def test_normal_close_releases_the_instance_lock_and_allows_reopening(self):
        name = self.inbox.name
        self.assertEqual(0, self.inbox._instance_lock.staleLockTime())
        self.inbox.close()
        replacement = DesktopInbox(name=name)
        self.addCleanup(replacement.close)
        self.assertTrue(replacement.server.isListening())

    def test_listener_startup_failure_does_not_leave_a_lock_behind(self):
        name = "video-encoder-test-" + uuid.uuid4().hex
        with patch.object(DesktopInbox, "listen", side_effect=OSError("Listener unavailable")):
            with self.assertRaises(OSError):
                DesktopInbox(name=name)
        replacement = DesktopInbox(name=name)
        self.addCleanup(replacement.close)
        self.assertTrue(replacement.server.isListening())

    def test_uncertain_delivery_never_retries_and_never_starts_another_instance(self):
        with patch.object(DesktopInbox, "forward", side_effect=OSError("No acknowledgement")) as forward:
            with self.assertRaises(OSError):
                start_inbox(None, "vidb-encoder://prepare?ticket=test")
        forward.assert_called_once()

    def test_a_successful_forward_needs_no_new_application_inbox(self):
        with patch.object(DesktopInbox, "forward", return_value=True):
            self.assertIsNone(start_inbox(None, "vidb-encoder://prepare?ticket=test"))
