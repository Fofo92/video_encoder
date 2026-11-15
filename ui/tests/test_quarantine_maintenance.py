import os
from pathlib import Path
import subprocess
import tempfile
import unittest


class QuarantineMaintenanceTest(unittest.TestCase):
    def run_maintenance(self, quarantine_status, trash_status):
        source = Path(__file__).resolve().parents[2] / 'script/quarantine-maintenance'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'script').mkdir()
            script = root / 'script/quarantine-maintenance'
            script.write_text(source.read_text())
            stub = root / 'bundle'
            stub.write_text(
                '#!/bin/sh\n'
                'printf "%s\\n" "$*" >> "$VIDEO_ENCODER_TEST_LOG"\n'
                'case "$*" in\n'
                '  *"project-trash sweep"*) exit "$VIDEO_ENCODER_TEST_TRASH_STATUS" ;;\n'
                '  *) exit "$VIDEO_ENCODER_TEST_QUARANTINE_STATUS" ;;\n'
                'esac\n')
            stub.chmod(0o755)
            log = root / 'calls.log'
            environment = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'],
                               VIDEO_ENCODER_TEST_LOG=str(log),
                               VIDEO_ENCODER_TEST_QUARANTINE_STATUS=str(quarantine_status),
                               VIDEO_ENCODER_TEST_TRASH_STATUS=str(trash_status))
            result = subprocess.run(['bash', str(script)], env=environment, capture_output=True, text=True)
            commands = log.read_text().splitlines()
        self.assertEqual(2, len(commands))
        self.assertIn('quarantine sweep --apply', commands[0])
        self.assertIn('project-trash sweep --apply', commands[1])
        return result.returncode

    def test_same_maintenance_pass_handles_both_retention_policies(self):
        self.assertEqual(0, self.run_maintenance(0, 0))

    def test_quarantine_failure_does_not_skip_project_trash(self):
        self.assertEqual(7, self.run_maintenance(7, 0))

    def test_project_trash_failure_marks_the_service_failed(self):
        self.assertEqual(9, self.run_maintenance(0, 9))


if __name__ == '__main__':
    unittest.main()
