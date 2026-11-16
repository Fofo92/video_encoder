import os
from pathlib import Path
import tempfile
import unittest

from video_encoder_ui.desktop_instance import other_application_pids


class DesktopInstanceTest(unittest.TestCase):
    def test_only_another_desktop_application_is_reported_not_tests_or_encoders(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            commands = {"10": b"python3\0-m\0video_encoder_ui.application\0",
                        "11": b"python3\0-m\0video_encoder_ui.application\0vidb-encoder://prepare\0",
                        "12": b"ruby\0bin/video_encoder\0run-trim-exports\0--once\0",
                        "13": b"python3\0ui/run_tests.py\0", "14": b"melt-7\0project.mlt\0"}
            for pid, command in commands.items():
                path = root / pid
                path.mkdir()
                (path / "cmdline").write_bytes(command)
            self.assertEqual([11], other_application_pids(root, own_pid=10, uid=os.getuid()))
            self.assertEqual([], other_application_pids(root, own_pid=10, uid=os.getuid() + 1))

    def test_processes_disappearing_during_inspection_do_not_prevent_launching(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "15").mkdir()
            self.assertEqual([], other_application_pids(root, own_pid=10))
        self.assertEqual([], other_application_pids(root, own_pid=10))
