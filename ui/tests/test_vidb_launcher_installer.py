from pathlib import Path
import runpy
import subprocess
import sys
import unittest


class VidbLauncherInstallerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = Path(__file__).resolve().parents[2] / "bin/install-vidb-launcher"
        cls.module = runpy.run_path(str(cls.script))

    def test_desktop_argument_quoting_preserves_spaces_percentages_and_one_url_argument(self):
        entry = self.module['desktop_entry'](Path('/home/nom composé/100%/video_encoder_ui'))
        self.assertIn('Exec=/bin/sh "/home/nom composé/100%%/video_encoder_ui" %u\n', entry)
        self.assertIn('MimeType=x-scheme-handler/vidb-encoder;', entry)
        with self.assertRaises(ValueError):
            self.module['desktop_entry'](Path('/home/bad\npath/video_encoder_ui'))

    def test_dry_run_needs_no_desktop_registration_or_running_encoder(self):
        result = subprocess.run([sys.executable, str(self.script), '--dry-run'],
                                check=True, text=True, capture_output=True)
        self.assertIn('[Desktop Entry]', result.stdout)
        self.assertIn('video_encoder_ui" %u', result.stdout)
