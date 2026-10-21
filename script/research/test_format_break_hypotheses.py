import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import numpy as np
from format_break_hypotheses import plan_format_review, cached_format_review
from refine_overlay_review import refine_format_window
from export_indexed_windows import source_identity


class FormatBreakHypothesesTest(unittest.TestCase):
    def labels(self, breaks):
        labels=np.ones(5*1800,dtype=np.int8)
        for start,end in breaks:labels[start*5:end*5]=0
        return labels

    def test_positive_full_frame_excursions_are_paired_without_fixed_break_count(self):
        for breaks in [[],[(300,360)],[(300,360),(900,980)],[(300,360),(700,760),(1200,1260)]]:
            report=plan_format_review(self.labels(breaks),0,1800*25-1)
            self.assertEqual(len(report['groups']),len(breaks))
            self.assertEqual(len(report['windows']),2*len(breaks))
            self.assertFalse(report['reviewed_interior_cuts_used'])
            self.assertFalse(report['source_editor_mapping_verified'])
            for group,(start,end) in zip(report['groups'],breaks):
                self.assertEqual(group['transition_brackets_seconds'],[[start-.2,float(start)],[end-.2,float(end)]])

    def test_dark_scene_gaps_and_full_frame_programmes_do_not_become_breaks(self):
        labels=self.labels([]);labels[300*5:400*5]=-1
        self.assertEqual(plan_format_review(labels,0,len(labels)*5-1)['groups'],[])
        report=plan_format_review(np.zeros_like(labels),0,len(labels)*5-1)
        self.assertEqual(report['status'],'needs_review')
        self.assertEqual(report['windows'],[])

    def test_unknown_return_does_not_move_to_the_end_of_a_late_stable_anchor(self):
        labels=self.labels([(300,360)])
        labels[365*5:385*5]=-1
        report=plan_format_review(labels,0,len(labels)*5-1)
        self.assertEqual(report['groups'][0]['transition_brackets_seconds'][1],[359.8,360.])
        self.assertLess(report['windows'][1]['end_decoded_frame_exclusive'],385*25)

    def test_bounds_and_wide_or_mixed_excursions_cannot_silently_form_a_montage(self):
        labels=self.labels([(300,360),(900,980)])
        report=plan_format_review(labels,500*25,1500*25)
        self.assertEqual(len(report['groups']),1)
        self.assertTrue(all(w['first_decoded_frame']>=500*25 and w['end_decoded_frame_exclusive']<=1500*25+1 for w in report['windows']))
        for first,last in [(True,100),(0,len(labels)*5),(100,0)]:
            with self.assertRaises(ValueError):plan_format_review(labels,first,last)
        mixed=self.labels([])
        mixed[300*5:330*5]=0;mixed[330*5:370*5]=-1
        report=plan_format_review(mixed,0,len(mixed)*5-1)
        self.assertEqual(report['status'],'needs_review')
        self.assertTrue(report['unresolved_groups'])
        overlong=np.ones(5000*5,dtype=np.int8);overlong[300*5:1300*5]=0
        report=plan_format_review(overlong,0,len(overlong)*5-1)
        self.assertEqual(report['status'],'needs_review')
        self.assertTrue(report['unresolved_groups'])

    def test_native_refinement_uses_format_context_and_exact_kept_frame_conventions(self):
        boxed=np.full((300,90,160,3),100,dtype=np.uint8)
        boxed[:,:12]=0;boxed[:,-12:]=0
        full=np.full_like(boxed,200)
        for role,frames,expected in [('departure',np.concatenate([boxed[:150],full[:150]]),1149),
                                     ('resume',np.concatenate([full[:150],boxed[:150]]),1150)]:
            window={'candidate_role':role,'group_index':1,'first_decoded_frame':1000,
                    'format_transition_bracket_seconds':[46.,46.2]}
            result=refine_format_window(frames,window)
            self.assertEqual(result['status'],'candidate_raccord',result)
            self.assertEqual(result['candidate_kept_decoded_frame'],expected)
            self.assertTrue(result['needs_manual_review'])
        result=refine_format_window(full,window)
        self.assertEqual(result['status'],'unresolved_no_format_transition')

    def test_sealed_cache_can_be_read_without_starting_a_decoder_and_tampering_fails(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.m2t';source.write_bytes(b'original')
            cache=root/'sampled-rgb.bin'
            # Uniform full-frame capture must abstain, not manufacture boundaries.
            cache.write_bytes(np.full((1000,18,32,3),100,dtype=np.uint8).tobytes())
            manifest={'status':'completed','source':str(source),'source_identity':source_identity(source),
                      'cache_path':str(cache),'sampled_frames':1000,'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest()}
            (root/'manifest.json').write_text(json.dumps(manifest))
            with mock.patch('subprocess.Popen',side_effect=AssertionError('A decoder was started')):
                result=cached_format_review(source,root,0,4999)
            self.assertEqual(result['status'],'needs_review')
            self.assertFalse(result['original_recording_decoded'])
            cache.write_bytes(b'bad')
            with self.assertRaises(ValueError):cached_format_review(source,root,0,4999)


if __name__=='__main__':unittest.main()
