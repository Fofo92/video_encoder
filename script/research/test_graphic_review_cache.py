import json
from pathlib import Path
import tempfile
import unittest
from export_indexed_windows import source_identity
from graphic_review_cache import completed_scan,completed_review,digest,copy_review
from prepare_overlay_review import plan
from stable_overlay_signals import GRAPHIC_ALGORITHM_REVISION


class GraphicReviewCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.m2t';self.source.write_bytes(b'source')
        self.observations=[self.root/'one.mp4',self.root/'two.mp4']
        for path in self.observations:path.write_bytes(b'observation')
        self.scan=self.root/'previous/scan/report.json';self.scan.parent.mkdir(parents=True)
        self.report={'status':'completed','source':str(self.source),'source_identity':source_identity(self.source),
                     'edge_mode':'both','sample_fps':5,'threshold':.8,'minimum_samples':3,'sampled_frames':1000,
                     'algorithm_revision':GRAPHIC_ALGORITHM_REVISION,
                     'observations':[{'path':str(p),'identity':source_identity(p),'sha256':digest(p)} for p in self.observations],
                     'learned_graphics':[{'source_shape':[360,640],'edge_mode':'white',
                                          'selection':'largest_shared_edge_region; unclassified graphic'}],
                     'occurrences_by_hypothesis':{'white':[]},'hypothesis_abstentions':{'contrast':'no support'},
                     'occurrences':[{'start_seconds':20.,'end_seconds_exclusive':21.},
                                    {'start_seconds':100.,'end_seconds_exclusive':101.}]}
        self.save()

    def save(self):self.scan.write_text(json.dumps(self.report))

    def native(self):
        grouping,windows=plan(self.report,0,200)
        directory=self.root/'previous/raccords';directory.mkdir()
        for row in windows:
            clip=directory/row['name'];clip.write_bytes(b'verified native pixels');row['sha256']=digest(clip)
        manifest={'status':'export_complete_editor_alignment_unverified','fps':25,'source':str(self.source),
                  'source_identity':source_identity(self.source),'presence_report_sha256':digest(self.scan),
                  'groups':grouping,'windows':windows}
        (directory/'frame-map.json').write_text(json.dumps(manifest))
        return directory

    def test_completed_scan_reuses_only_same_source_observations_and_settings(self):
        self.assertEqual(completed_scan(self.root,self.source,self.observations),self.scan)
        self.report.pop('algorithm_revision');self.save()
        self.assertIsNone(completed_scan(self.root,self.source,self.observations))
        self.report['algorithm_revision']='shared-graphic-v1';self.save()
        self.assertIsNone(completed_scan(self.root,self.source,self.observations))
        self.report['algorithm_revision']=GRAPHIC_ALGORITHM_REVISION;self.save()
        self.observations[0].write_bytes(b'manual change')
        self.assertIsNone(completed_scan(self.root,self.source,self.observations))

    def test_failed_incomplete_or_different_parameter_scan_is_not_reused(self):
        self.scan.write_text('[]')
        self.assertIsNone(completed_scan(self.root,self.source,self.observations))
        self.save()
        for key,value in [('status','running'),('threshold',.7),('sample_fps',10),('edge_mode','white'),
                          ('algorithm_revision','unsupported')]:
            original=self.report[key];self.report[key]=value;self.save()
            self.assertIsNone(completed_scan(self.root,self.source,self.observations))
            self.report[key]=original
        self.save();self.source.write_bytes(b'changed recording')
        self.assertIsNone(completed_scan(self.root,self.source,self.observations))

    def test_native_reuse_preserves_hashes_and_archive_without_unrelated_files(self):
        previous=self.native();(previous/'unrelated-project.mkv').write_bytes(b'do not copy')
        self.assertEqual(completed_review(self.root,self.source,self.scan,0,4999),previous)
        self.assertIsNone(completed_review(self.root,self.source,self.scan,1,4999))
        target=self.root/'retry/raccords';copy_review(previous,target)
        self.assertEqual((target/'frame-map.json').read_bytes(),(previous/'frame-map.json').read_bytes())
        self.assertFalse((target/'unrelated-project.mkv').exists())
        self.assertTrue((self.root/'retry/raccords.tar.gz').is_file())

    def test_modified_native_pixels_or_mapping_block_reuse(self):
        previous=self.native();(previous/'departure-1.mp4').write_bytes(b'changed pixels')
        self.assertIsNone(completed_review(self.root,self.source,self.scan,0,4999))


if __name__=='__main__':unittest.main()
