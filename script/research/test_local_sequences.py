import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from discover_local_sequences import discover_patch, run, verified_correlation


class LocalSequencesTest(unittest.TestCase):
    def test_moving_local_sequence_repeats_across_separated_occurrences(self):
        rng=np.random.default_rng(13)
        frames=rng.integers(0,256,(650,144),dtype=np.uint8)
        motif=rng.integers(30,180,(15,144),dtype=np.uint8)
        for start,brightness in [(20,0),(240,20),(460,40)]:
            frames[start:start+15]=motif+brightness
        result=discover_patch(frames)
        self.assertTrue(any(all(any(abs(occ['core_start_seconds']-start/5)<2
                                       for occ in group['occurrences'])
                                  for start in [20,240,460]) for group in result['groups']))
        self.assertNotIn('timeline',result)

    def test_static_graphics_are_not_motion_evidence(self):
        rng=np.random.default_rng(14)
        frame=rng.integers(0,256,(1,144),dtype=np.uint8)
        result=discover_patch(np.repeat(frame,650,axis=0))
        self.assertEqual(result['eligible_windows'],0)
        self.assertEqual(result['groups'],[])

    def test_same_colours_do_not_hide_opposite_temporal_variation(self):
        rng=np.random.default_rng(16)
        background=rng.uniform(40,180,(1,144)).astype('float32')
        motion=np.arange(10,dtype='float32')[:,None]*2
        a=background+motion
        b=background-motion
        self.assertGreater(np.corrcoef(a.reshape(-1),b.reshape(-1))[0,1],.8)
        self.assertIsNone(verified_correlation(a,b))
        self.assertIsNotNone(verified_correlation(a,a+20))

    def test_limits_are_reported_and_enforced(self):
        rng=np.random.default_rng(15)
        motif=rng.integers(0,256,(15,144),dtype=np.uint8)
        frames=np.tile(motif,(60,1))
        result=discover_patch(frames,max_pairs=10,max_bucket=2)
        self.assertLessEqual(result['comparisons'],10)
        self.assertTrue(result['pair_limit_reached'])
        self.assertTrue(result['bucket_limit_reached'])

    def test_modified_cache_is_rejected_without_accessing_source(self):
        with tempfile.TemporaryDirectory() as name:
            directory=Path(name)
            cache=directory/'sampled-rgb.bin'
            cache.write_bytes(bytes(10*1728))
            manifest={'status':'completed','sampled_frames':10,
                      'source':'/nonexistent/recording.m2t',
                      'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest()}
            (directory/'manifest.json').write_text(json.dumps(manifest))
            cache.write_bytes(bytes([1])*(10*1728))
            with self.assertRaisesRegex(ValueError,'modified'):
                run(directory)


if __name__=='__main__':unittest.main()
