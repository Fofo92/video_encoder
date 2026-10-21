import unittest
import numpy as np
from jingle_boundary_signals import boundary_evidence


class JingleBoundarySignalsTest(unittest.TestCase):
    def test_black_entry_and_exit_are_distinguished_without_accepting_cuts(self):
        frames=np.full((100,12,16,3),70,dtype=np.uint8)
        frames[25:30]=0
        frames[30:70]=220
        frames[70:]=20
        result=boundary_evidence(frames,(50,70))
        kinds={r['observation_frame']:r['kind'] for r in result['opening_candidates']}
        self.assertEqual(kinds[25],'enter_black')
        self.assertEqual(kinds[30],'exit_black')
        self.assertEqual(result['closing_candidates'][0]['observation_frame'],70)
        self.assertTrue(result['needs_manual_review'])
        self.assertNotIn('timeline',result)

    def test_internal_jingle_cut_remains_an_alternative(self):
        frames=np.full((100,12,16,3),20,dtype=np.uint8)
        frames[20:40]=150
        frames[40:70]=230
        result=boundary_evidence(frames,(55,70))
        indices={r['observation_frame'] for r in result['opening_candidates']}
        self.assertIn(20,indices)
        self.assertIn(40,indices)

    def test_motionless_clip_does_not_invent_a_boundary(self):
        frames=np.full((100,12,16,3),70,dtype=np.uint8)
        result=boundary_evidence(frames,(50,70))
        self.assertEqual(result['opening_candidates'],[])
        self.assertEqual(result['closing_candidates'],[])

    def test_graphic_start_transition_is_included_without_looking_past_the_anchor(self):
        frames=np.full((100,12,16,3),30,dtype=np.uint8)
        frames[50:70]=160
        frames[51:70]=230
        result=boundary_evidence(frames,(50,70))
        indices={r['observation_frame'] for r in result['opening_candidates']}
        self.assertIn(50,indices)
        self.assertNotIn(51,indices)

    def test_invalid_anchors_and_rates_are_rejected(self):
        frames=np.full((100,12,16,3),70,dtype=np.uint8)
        for anchor in [(-1,70),(70,50),(50,101)]:
            with self.assertRaises(ValueError):boundary_evidence(frames,anchor)
        with self.assertRaises(ValueError):boundary_evidence(frames,(50,70),fps=float('nan'))


if __name__=='__main__':unittest.main()
