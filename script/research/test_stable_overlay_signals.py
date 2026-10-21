import unittest
from unittest import mock
import numpy as np
from stable_overlay_signals import persistent_edges, shared_persistent_edges, overlay_candidates, presence_scores, refine_shared_candidate, contrast_edges, graphic_edges, peak_shape_agreement


class StableOverlaySignalsTest(unittest.TestCase):
    def test_sparse_shared_intersection_cannot_validate_unrelated_full_graphics(self):
        from scan_stable_overlays import learn_model, GraphicLearningAbstention
        clips=[]
        # Three repeated graphics and one different graphic share a sparse
        # scaffold. All four score highly against their learned intersection.
        for seed in [1,1,2,1]:
            frames=np.zeros((20,80,128,3),dtype=np.uint8)
            for index in range(20):frames[6:13,10+3*index,10+3*index]=255
            rng=np.random.default_rng(seed)
            for y,x in zip(rng.integers(10,68,80),rng.integers(10,68,80)):
                frames[6:13,y,x]=255
            clips.append(frames)
        with mock.patch('scan_stable_overlays.peak_shape_agreement',return_value={'minimum_pairwise_iou':1.}):
            previous=learn_model(clips)
        self.assertGreater(min(previous['training_peak_scores']),.8)
        with self.assertRaisesRegex(GraphicLearningAbstention,'shapes disagree'):
            learn_model(clips)

    def test_peak_shape_check_preserves_inversion_and_validates_sample_indices(self):
        clips=self.clips()
        original=clips[0]
        agreement=peak_shape_agreement([original,255-original],[8,8],[40,20,14,12],'contrast')
        self.assertEqual(agreement['minimum_pairwise_iou'],1.)
        for peaks,bbox in [([True,8],[40,20,14,12]),([8,99],[40,20,14,12]),([8,8],[0,0,999,999])]:
            with self.assertRaises(ValueError):peak_shape_agreement(clips[:2],peaks,bbox)

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

    def test_contrast_edges_are_invariant_to_colour_inversion(self):
        frames=self.clips()[0]
        np.testing.assert_array_equal(contrast_edges(frames),contrast_edges(255-frames))

    def test_uniform_colour_changes_and_flashes_do_not_establish_contrast_graphic(self):
        frames=np.zeros((20,40,64,3),dtype=np.uint8)
        frames[::2]=[200,80,120]
        self.assertFalse(persistent_edges(frames,edge_mode='contrast').any())
        frames[10,20:30,40:50]=255
        self.assertFalse(persistent_edges(frames,edge_mode='contrast').any())

    def test_contrast_rejects_bad_input_and_unknown_modes(self):
        with self.assertRaises(ValueError):contrast_edges(np.zeros((301,40,64,3),dtype=np.uint8))
        with self.assertRaises(ValueError):graphic_edges(self.clips()[0],'unknown')

    def test_contrast_model_transfers_to_held_out_inverted_graphic(self):
        from scan_stable_overlays import learn_model, scan_blocks
        clips=[]
        for seed in range(4):
            rng=np.random.default_rng(seed)
            frames=np.broadcast_to(rng.integers(20,80,(20,1,1,3),dtype=np.uint8),
                                   (20,40,64,3)).copy()
            frames[6:13,20:32,40:44]=240
            frames[6:13,28:32,40:54]=240
            clips.append(255-frames if seed%2 else frames)
        model=learn_model(clips[:3],edge_mode='contrast')
        self.assertEqual(model['edge_mode'],'contrast')
        x,y,w,h=model['crop']
        count,intervals=scan_blocks([clips[3][:,y:y+h,x:x+w]],model)
        self.assertEqual(count,20)
        self.assertEqual([(row['first_sample'],row['end_sample_exclusive']) for row in intervals],[(6,13)])


if __name__=='__main__':unittest.main()
