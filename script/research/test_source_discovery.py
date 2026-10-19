import unittest
import numpy as np
from discover_source_sequences import discover_source


class SourceDiscoveryTest(unittest.TestCase):
    def source(self):
        rng = np.random.default_rng(201)
        frames = rng.integers(0, 256, (650, 48), dtype=np.uint8)
        motif = rng.integers(0, 256, (15, 48), dtype=np.uint8)
        for start in [40, 250, 500]:
            frames[start:start + 15] = motif
        return frames

    def test_discovers_repeated_movement_without_observation_clips(self):
        result = discover_source(self.source())
        self.assertTrue(any(row['supporting_occurrences'] == 3 for row in result['candidates']))
        row = next(row for row in result['candidates'] if row['supporting_occurrences'] == 3)
        self.assertEqual([item['core_start_seconds'] for item in row['occurrences']], [8, 50, 100])
        self.assertEqual(row['classification'], 'unverified_repeated_visual_sequence')

    def test_does_not_count_nearby_windows_as_independent_occurrences(self):
        self.assertEqual(discover_source(self.source()[:150])['candidates'], [])

    def test_static_source_abstains(self):
        self.assertEqual(discover_source(np.zeros((650, 48), np.uint8))['candidates'], [])

    def test_comparison_limit_is_reported(self):
        result = discover_source(self.source(), max_pairs=1)
        self.assertEqual(result['comparisons'], 1)
        self.assertTrue(result['pair_limit_reached'])

    def test_short_source_abstains(self):
        self.assertEqual(discover_source(self.source()[:5])['candidates'], [])


class DiscoveryCacheTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        import json
        from pathlib import Path
        from export_indexed_windows import source_identity
        from discover_source_sequences import digest
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source.m2t'
        self.source.write_bytes(b'source untouched')
        self.cache_dir = self.root / 'cache'
        self.cache_dir.mkdir()
        self.cache = self.cache_dir / 'sampled-rgb.bin'
        np.random.default_rng(5).integers(0, 256, (20, 1728), dtype=np.uint8).tofile(self.cache)
        self.manifest = {'status': 'completed', 'source': str(self.source),
                         'source_identity': source_identity(self.source), 'sampled_frames': 20,
                         'cache_sha256': digest(self.cache)}
        self.manifest_path = self.cache_dir / 'manifest.json'
        self.manifest_path.write_text(json.dumps(self.manifest))

    def test_reuse_never_decodes_and_keeps_original_cache(self):
        from unittest.mock import patch
        from discover_source_sequences import run, digest
        before = digest(self.cache)
        with patch('discover_source_sequences.source_blocks', side_effect=AssertionError('must not decode')):
            result = run(self.source, self.root / 'new', self.cache_dir)
        self.assertTrue(result['reused_cache'])
        self.assertEqual(result['cache_integrity'], 'verified_sha256')
        self.assertEqual(digest(self.cache), before)

    def test_modified_cache_is_rejected_even_at_the_same_size(self):
        from discover_source_sequences import load_cache
        with self.cache.open('r+b') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'checksum'):
            load_cache(self.cache_dir, self.source)

    def test_modified_source_is_rejected(self):
        from discover_source_sequences import load_cache
        self.source.write_bytes(b'new source')
        with self.assertRaisesRegex(ValueError, 'modified source'):
            load_cache(self.cache_dir, self.source)

    def test_legacy_cache_is_identified_without_inventing_a_historical_digest(self):
        import json
        from discover_source_sequences import load_cache
        del self.manifest['cache_sha256']
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.assertEqual(load_cache(self.cache_dir, self.source)[3], 'legacy_cache_no_original_digest')

    def test_incomplete_or_truncated_cache_is_rejected(self):
        import json
        from discover_source_sequences import load_cache
        self.cache.write_bytes(b'truncated')
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            load_cache(self.cache_dir, self.source)
        self.manifest['status'] = 'decoding'
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            load_cache(self.cache_dir, self.source)
