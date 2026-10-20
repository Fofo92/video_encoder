import unittest
import numpy as np
from stable_overlay_signals import persistent_edges, shared_persistent_edges, overlay_candidates, presence_scores, refine_shared_candidate


class StableOverlaySignalsTest(unittest.TestCase):
    def clips(self):
        clips=[]
        for seed in range(4):
            rng=np.random.default_rng(seed)
            a=rng.integers(0,150,(20,40,64,3),dtype=np.uint8)
            # A white graphic appears without identical backgrounds or known input times.
            a[6:13,20:32,40:44]=255
            a[6:13,28:32,40:54]=255
            clips.append(a)
        return clips

    def test_three_clips_locate_graphic_without_spatial_input_and_transfer_to_fourth(self):
        clips=self.clips()
        shared=shared_persistent_edges(clips[:3])
        candidates=overlay_candidates(shared)
        self.assertTrue(candidates)
        bbox=candidates[0]['bbox_xywh']
        self.assertLessEqual(bbox[0],40)
        self.assertGreaterEqual(bbox[0]+bbox[2],54)
        scores=presence_scores(clips[3],shared,bbox)
        self.assertGreater(scores[6:13].min(),.95)
        self.assertLess(scores[:6].max(),.55)
        self.assertLess(scores[13:].max(),.55)

    def test_refinement_uses_only_training_observations_and_keeps_held_out_detection(self):
        clips=self.clips()
        shared=shared_persistent_edges(clips[:3])
        bbox=overlay_candidates(shared)[0]['bbox_xywh']
        refined,peaks=refine_shared_candidate(clips[:3],shared,bbox)
        self.assertEqual(len(peaks),2)
        self.assertTrue(all(len(row)==3 for row in peaks))
        scores=presence_scores(clips[3],refined,bbox)
        self.assertGreater(scores[6:13].min(),.95)
        self.assertLess(scores[:6].max(),.55)

    def test_white_field_is_not_a_graphic(self):
        a=np.full((20,40,64,3),255,dtype=np.uint8)
        self.assertFalse(persistent_edges(a).any())

    def test_one_frame_flash_does_not_establish_persistence(self):
        a=np.zeros((20,40,64,3),dtype=np.uint8)
        a[10,20:30,40:50]=255
        self.assertFalse(persistent_edges(a).any())

    def test_graphics_at_different_locations_do_not_form_a_shared_overlay(self):
        clips=self.clips()
        clips[1]=np.roll(clips[1],20,axis=2)
        self.assertFalse(shared_persistent_edges(clips[:2]).any())

    def test_geometry_and_resource_limits_are_checked(self):
        clips=self.clips()
        with self.assertRaises(ValueError):shared_persistent_edges(clips[:1])
        with self.assertRaises(ValueError):persistent_edges(np.zeros((301,40,64,3),dtype=np.uint8))
        with self.assertRaises(ValueError):presence_scores(clips[0],np.zeros((40,64),dtype=bool),[0,0,20,20])


if __name__=='__main__':unittest.main()
