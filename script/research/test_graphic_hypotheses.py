import unittest
import numpy as np
from scan_stable_overlays import (learn_model,learn_hypotheses,combined_crop,
                                 scan_blocks,scan_hypotheses,merge_occurrences)
from group_overlay_occurrences import group_occurrences
from prepare_overlay_review import plan


class GraphicHypothesesTest(unittest.TestCase):
    def models(self):
        clips=[]
        for _ in range(2):
            a=np.zeros((20,40,64,3),dtype=np.uint8)
            a[6:13,20:32,40:44]=255;a[6:13,28:32,40:54]=255
            clips.append(a)
        return [learn_model(clips,'white'),learn_model([np.roll(c,-24,axis=2) for c in clips],'contrast')]

    def test_two_models_share_one_stream_and_preserve_individual_results_across_blocks(self):
        models=self.models()
        source=np.zeros((23,40,64,3),dtype=np.uint8)
        source[9:16,20:32,40:44]=255;source[9:16,28:32,40:54]=255
        source[14:21,20:32,16:20]=255;source[14:21,28:32,16:30]=255
        x,y,w,h=combined_crop(models);crop=source[:,y:y+h,x:x+w]
        read=[]
        def blocks():
            for first,last in [(0,11),(11,13),(13,17),(17,21),(21,23)]:
                read.append((first,last));yield crop[first:last]
        progress=[]
        count,merged,per_mode=scan_hypotheses(blocks(),models,progress.append)
        self.assertEqual(count,23);self.assertEqual(len(read),5)
        self.assertEqual(progress,[11,13,17,21,23])
        for model in models:
            x,y,w,h=model['crop']
            self.assertEqual(scan_blocks([source[:,y:y+h,x:x+w]],model)[1],per_mode[model['edge_mode']])
        self.assertEqual([(r['first_sample'],r['end_sample_exclusive']) for r in merged],[(9,21)])
        self.assertEqual(merged[0]['signal_modes'],['contrast','white'])
        self.assertEqual(len(merged[0]['evidence']),2)
        self.assertNotIn('peak_score',merged[0])

    def test_white_abstention_does_not_prevent_contrast_learning(self):
        a=np.full((20,40,64,3),[120,40,80],dtype=np.uint8)
        a[6:13,20:32,40:44]=0;a[6:13,28:32,40:54]=0
        models,abstentions=learn_hypotheses([a,a.copy()])
        self.assertEqual([m['edge_mode'] for m in models],['contrast'])
        self.assertEqual(list(abstentions),['white'])
        with self.assertRaisesRegex(ValueError,'Neither graphic hypothesis'):
            learn_hypotheses([np.zeros_like(a),np.zeros_like(a)])

    def test_union_keeps_disjoint_and_touching_events_separate(self):
        def row(first,last):return {'first_sample':first,'end_sample_exclusive':last}
        merged=merge_occurrences({'white':[row(100,105),row(400,405)],
                                  'contrast':[row(102,108),row(108,111),row(600,605)]})
        self.assertEqual([(r['first_sample'],r['end_sample_exclusive']) for r in merged],
                         [(100,108),(108,111),(400,405),(600,605)])
        self.assertEqual(merged[1]['signal_modes'],['contrast'])
        report={'status':'completed','sample_fps':5,'occurrences':merged}
        grouped=group_occurrences(report,0,200)
        self.assertEqual(grouped['inside_occurrence_count'],4)
        groups,windows=plan(report,0,200)
        self.assertEqual(len(windows),2)
        self.assertEqual(windows[0]['candidate_role'],'departure')
        self.assertEqual(windows[1]['candidate_role'],'resume')

    def test_invalid_or_incompatible_streams_are_rejected(self):
        models=self.models()
        with self.assertRaises(ValueError):combined_crop(models+models[:1])
        with self.assertRaises(ValueError):scan_hypotheses([np.zeros((5,8,8,3),dtype=np.uint8)],models)
        with self.assertRaises(ValueError):merge_occurrences({'white':[{'first_sample':4,'end_sample_exclusive':3}]})
        with self.assertRaises(ValueError):merge_occurrences({'white':[{'first_sample':4,'end_sample_exclusive':8},
                                                                       {'first_sample':7,'end_sample_exclusive':9}]})


if __name__=='__main__':unittest.main()
