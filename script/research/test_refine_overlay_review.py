import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from refine_overlay_review import refine_window,refine


class RefineOverlayReviewTest(unittest.TestCase):
    def frames(self):
        a=np.full((400,12,16,3),30,dtype=np.uint8)
        a[100:130]=160;a[130:230]=190;a[230:]=20
        return a

    def window(self,role):
        return {'candidate_role':role,'first_decoded_frame':10000,
                'approximate_graphic_local_frame':150,'group_index':1}

    def test_departure_keeps_frame_before_transition(self):
        r=refine_window(self.frames(),self.window('departure'),{'start_seconds':20.,'end_seconds_exclusive':22.8})
        self.assertEqual(r['status'],'candidate_raccord')
        self.assertEqual(r['candidate_transition_decoded_frame'],10100)
        self.assertEqual(r['candidate_kept_decoded_frame'],10099)
        self.assertTrue(r['needs_manual_review'])
        self.assertNotIn('timeline',r)

    def test_resume_keeps_transition_frame_without_off_by_one(self):
        r=refine_window(self.frames(),self.window('resume'),{'start_seconds':20.,'end_seconds_exclusive':22.8})
        self.assertEqual(r['candidate_kept_decoded_frame'],10230)
        self.assertEqual(r['kept_frame_meaning'],'first_kept')

    def test_comparable_internal_scene_change_remains_ambiguous(self):
        a=self.frames();a[100:130]=130;a[130:230]=240
        r=refine_window(a,self.window('departure'),{'start_seconds':20.,'end_seconds_exclusive':22.8})
        self.assertEqual(r['status'],'ambiguous_competing_transitions')
        self.assertNotIn('candidate_kept_decoded_frame',r)

    def test_dominant_entry_into_black_does_not_become_a_cut(self):
        a=np.full((400,12,16,3),240,dtype=np.uint8)
        a[100:110]=0;a[110:230]=160
        r=refine_window(a,self.window('departure'),{'start_seconds':20.,'end_seconds_exclusive':22.8})
        self.assertEqual(r['status'],'ambiguous_black_entry')
        self.assertNotIn('candidate_kept_decoded_frame',r)

    def test_no_transition_does_not_become_a_no_advertisement_claim(self):
        a=np.full((400,12,16,3),70,dtype=np.uint8)
        r=refine_window(a,self.window('resume'),{'start_seconds':20.,'end_seconds_exclusive':22.8})
        self.assertEqual(r['status'],'unresolved_no_transition')
        self.assertTrue(r['needs_manual_review'])

    def test_changed_clip_is_rejected_before_decoding(self):
        with tempfile.TemporaryDirectory() as name:
            p=Path(name);(p/'clip.mp4').write_bytes(b'changed')
            m={'status':'export_complete_editor_alignment_unverified','fps':25,
               'groups':{'groups':[{'status':'candidate_temporal_group'}]},
               'windows':[{'candidate_role':'departure','group_index':1,'name':'clip.mp4','sha256':'wrong'},{}]}
            (p/'frame-map.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'checksum'):refine(p)


if __name__=='__main__':unittest.main()
