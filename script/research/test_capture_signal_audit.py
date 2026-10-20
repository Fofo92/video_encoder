import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from audit_capture_signals import audit_cache, motion_window_rmse, latest_cache


class CachedSignalAuditTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        frames = np.full((60,18,32,3), 90, dtype=np.uint8)
        frames[:20,:2] = 0
        frames[:20,-2:] = 0
        frames[40:,:2] = 0
        frames[40:,-2:] = 0
        self.cache = self.root / 'sampled-rgb.bin'
        frames.tofile(self.cache)
        self.manifest = {'status': 'completed', 'source': '/unavailable-recording.m2t',
                         'sampled_frames': 60, 'cache_path': '/unavailable-cache/sampled-rgb.bin',
                         'cache_sha256': hashlib.sha256(self.cache.read_bytes()).hexdigest()}
        self.path = self.root / 'manifest.json'
        self.path.write_text(json.dumps(self.manifest))

    def test_offline_audit_uses_local_sealed_pixels_without_source_or_decoder(self):
        with patch('subprocess.Popen', side_effect=AssertionError('no decoder')):
            result = audit_cache(self.root)
        self.assertFalse(result['original_recording_accessed'])
        self.assertFalse(result['original_source_identity_rechecked'])
        self.assertEqual(len(result['band_audit']['format_changes']), 2)
        self.assertEqual(len(self.cache.read_bytes()), 60 * 1728)
        self.assertNotIn('project', result)

    def test_changed_pixels_and_missing_seal_are_rejected(self):
        with self.cache.open('r+b') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            audit_cache(self.root)
        self.manifest.pop('cache_sha256')
        self.path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, 'sealed'):
            audit_cache(self.root)

    def test_truncated_cache_is_rejected(self):
        self.cache.write_bytes(b'short')
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            audit_cache(self.root)

    def test_cache_is_found_without_requiring_the_original_recording(self):
        self.assertEqual(latest_cache(self.root, Path(self.manifest['source'])), self.root)
        with self.assertRaisesRegex(ValueError, 'No completed sealed cache'):
            latest_cache(self.root, Path('/different-recording.m2t'))

    def test_low_motion_windows_can_be_measured_without_changing_default_threshold(self):
        frames = np.full((20,48), 100, dtype=np.uint8)
        frames[::2] += 1
        scores = motion_window_rmse(frames)
        np.testing.assert_allclose(scores, 1)
        self.assertEqual(int(np.sum(scores >= 2)), 0)
        self.assertEqual(int(np.sum(scores >= .5)), 11)
