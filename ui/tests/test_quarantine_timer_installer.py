import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch


def installer():
    path = Path(__file__).resolve().parents[2] / 'bin/install-quarantine-timer'
    loader = importlib.machinery.SourceFileLoader('quarantine_timer_installer', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class QuarantineTimerInstallerTest(unittest.TestCase):
    def test_installation_previews_before_enabling_only_the_timer(self):
        module = installer()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            environment = {'PATH': '/opt/ruby/bin:/usr/bin:/bin', 'XDG_CONFIG_HOME': str(root / 'config')}
            output = {'format': 'video_encoder.quarantine', 'errors': [], 'entries': []}
            with patch.object(module, '__file__', str(root / 'encoder/bin/install-quarantine-timer')), \
                    patch.dict(os.environ, environment, clear=True), \
                    patch.object(module.subprocess, 'run', return_value=Mock(stdout=json.dumps(output))) as run:
                module.main()
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(['bundle', 'exec', 'ruby', 'bin/video_encoder', 'quarantine', 'sweep'], commands[0])
            self.assertEqual(['systemctl', '--user', 'enable', '--now', 'video-encoder-quarantine.timer'], commands[2])
            self.assertFalse(any('--apply' in command for command in commands))
            service = (root / 'config/systemd/user/video-encoder-quarantine.service').read_text()
            self.assertIn('PATH=/opt/ruby/bin:/usr/bin:/bin', service)
            self.assertIn('script/quarantine-maintenance', service)
            timer = (root / 'config/systemd/user/video-encoder-quarantine.timer').read_text()
            self.assertIn('03:30:00', timer)
            self.assertIn('Persistent=true', timer)

    def test_failed_preview_does_not_install_or_enable_a_timer(self):
        module = installer()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(module, '__file__', str(root / 'encoder/bin/install-quarantine-timer')), \
                    patch.dict(os.environ, {'PATH': '/usr/bin:/bin', 'XDG_CONFIG_HOME': str(root / 'config')}, clear=True), \
                    patch.object(module.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'bundle')) as run:
                with self.assertRaises(subprocess.CalledProcessError):
                    module.main()
            self.assertEqual(1, run.call_count)
            self.assertFalse((root / 'config/systemd/user/video-encoder-quarantine.timer').exists())

    def test_unit_quoting_preserves_spaces_and_percent_and_rejects_multiline_values(self):
        module = installer()
        self.assertEqual('"/a b/%%capture"', module.quoted('/a b/%capture'))
        with self.assertRaises(ValueError):
            module.quoted('one\ntwo')
