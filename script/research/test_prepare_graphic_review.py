import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import numpy as np
from unittest import mock
from prepare_graphic_review import run
from export_indexed_windows import source_identity


class PrepareGraphicReviewTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg unavailable')
    def test_real_format_cache_to_native_review_without_graphic_scan_and_reuses_export(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'format.mkv'
            enable='lt(t,180)+gte(t,240)'
            filters=','.join([f"drawbox=x=0:y={y}:w=iw:h=12:color=black:t=fill:enable='{enable}'" for y in [0,78]])
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x646464:s=160x90:r=25:d=420',
                            '-vf',filters,'-c:v','ffv1',str(source)],check=True)
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            pixels=np.full((2100,18,32,3),100,dtype=np.uint8)
            pixels[:900,:2]=0;pixels[:900,-2:]=0
            pixels[1200:,:2]=0;pixels[1200:,-2:]=0
            cache=root/'sampled-rgb.bin';cache.write_bytes(pixels.tobytes())
            (root/'manifest.json').write_text(json.dumps({'status':'completed','source':str(source),
                'source_identity':source_identity(source),'sampled_frames':2100,'cache_path':str(cache),
                'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest()}))
            with mock.patch('prepare_graphic_review.scan',side_effect=AssertionError('Full graphic scan started')):
                path=run(source,[],0,10499,root/'review',cache_root=root)
            report=json.loads(path.read_text())
            self.assertEqual(report['status'],'ready_for_review',report)
            self.assertEqual(report['preparation_method'],'format_hypotheses')
            self.assertFalse(report['recording_scan_started'])
            result=json.loads((path.parent/'raccords.json').read_text())
            self.assertEqual(result['review_origin'],'format_hypotheses')
            self.assertEqual([r['candidate_kept_decoded_frame'] for r in result['raccords']],[4499,6000])
            self.assertTrue(result['needs_manual_review'])
            with mock.patch('prepare_graphic_review.scan',side_effect=AssertionError('Full scan repeated')), \
                 mock.patch('prepare_graphic_review.export_windows',side_effect=AssertionError('Native export repeated')):
                retry=run(source,[],0,10499,root/'retry',cache_root=root)
            repeated=json.loads(retry.read_text())
            self.assertEqual(repeated['status'],'ready_for_review')
            self.assertEqual(repeated['reused_review_from'],str(root/'review/raccords'))
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)

    def test_learning_abstention_is_a_review_case_without_extraction_or_refinement(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.mkv';source.write_bytes(b'original')
            presence=root/'presence.json'
            presence.write_text(json.dumps({'status':'needs_review','sampled_frames':0,
                'source_identity':source_identity(source),'reason':'Observations incohérentes ; scan non lancé.',
                'learning_abstention':'shapes disagree'}))
            with mock.patch('prepare_graphic_review.verify_native_rate'), \
                 mock.patch('prepare_graphic_review.scan',return_value=presence), \
                 mock.patch('prepare_graphic_review.export') as extract, \
                 mock.patch('prepare_graphic_review.refine') as refinement:
                path=run(source,[],0,2499,root/'output')
            report=json.loads(path.read_text())
            self.assertEqual(report['status'],'needs_review')
            self.assertEqual(report['candidate_raccord_count'],0)
            self.assertFalse(report['recording_scan_started'])
            self.assertEqual(report['learning_abstention'],'shapes disagree')
            extract.assert_not_called();refinement.assert_not_called()

    def test_scan_failure_stops_later_stages_and_retains_failure_report(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.mkv';source.write_bytes(b'original')
            for error,status in [(ValueError('scan failed'),'failed'),(KeyboardInterrupt(),'interrupted')]:
                output=root/status
                with mock.patch('prepare_graphic_review.verify_native_rate'), \
                     mock.patch('prepare_graphic_review.scan',side_effect=error), \
                     mock.patch('prepare_graphic_review.export') as extract:
                    with self.assertRaises(type(error)):run(source,[],0,2499,output)
                extract.assert_not_called()
                report=json.loads((output/'pipeline.json').read_text())
                self.assertEqual(report['status'],status)
                self.assertEqual(report['stage'],'scanning')
                self.assertEqual(source.read_bytes(),b'original')

    def test_no_graphic_group_is_a_review_case_without_extraction(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.mkv';source.write_bytes(b'original')
            presence=root/'presence.json';presence.write_text(json.dumps({'status':'completed','sample_fps':5,
                                                                         'source_identity':source_identity(source),'occurrences':[]}))
            with mock.patch('prepare_graphic_review.verify_native_rate'), \
                 mock.patch('prepare_graphic_review.scan',return_value=presence) as scan, \
                 mock.patch('prepare_graphic_review.export') as extract:
                report_path=run(source,[],1,2499,root/'output')
            extract.assert_not_called()
            self.assertEqual(scan.call_args.kwargs['edge_mode'],'both')
            report=json.loads(report_path.read_text())
            self.assertEqual(report['status'],'needs_review')
            self.assertEqual(report['programme_bounds_seconds'],[.04,100.])
            self.assertTrue((root/'output/groups.json').is_file())

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg unavailable')
    def test_real_source_to_paired_raccords_without_detector_or_interior_cut_input(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.mkv'
            filters=[]
            for start,end,background,foreground in [(20,22,'0x8040a0','white'),(83,85,'0x7fbf5f','black')]:
                enable=f"gte(t,{start})*lt(t,{end})"
                filters += [f"drawbox=x=0:y=0:w=iw:h=ih:color={background}:t=fill:enable='{enable}'",
                            f"drawbox=x=160:y=70:w=14:h=50:color={foreground}:t=fill:enable='{enable}'",
                            f"drawbox=x=160:y=106:w=55:h=14:color={foreground}:t=fill:enable='{enable}'"]
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=0x303030:s=320x180:r=25:d=100',
                            '-vf',','.join(filters),'-c:v','ffv1',str(source)],check=True)
            before=hashlib.sha256(source.read_bytes()).hexdigest()
            discovery=root/'resultat.json'
            discovery.write_text(json.dumps({'status':'experimental','sample_fps':5,
                                              'source':str(source),'source_identity':source_identity(source),
                                              'index_limits_reached':True,
                                              'candidates':[{'occurrences':[{'core_start_seconds':t,'core_end_seconds':t+2}
                                                                            for t in [20,83]]}]}))
            report_path=run(source,[],0,2499,root/'review',discovery_report=discovery)
            report=json.loads(report_path.read_text())
            self.assertEqual(report['status'],'ready_for_review', (root/'review/raccords.json').read_text())
            self.assertTrue(report['needs_manual_review'])
            self.assertEqual(report['observation_manifest_sha256'],hashlib.sha256((root/'review/observations/frame-map.json').read_bytes()).hexdigest())
            self.assertTrue(report['discovery_search_partial'])
            self.assertFalse(report['source_editor_mapping_verified'])
            self.assertEqual(report['candidate_group_count'],1)
            self.assertEqual(report['candidate_raccord_count'],2)
            raccords=json.loads((root/'review/raccords.json').read_text())
            self.assertEqual(raccords['review_origin'],'graphic_hypotheses')
            self.assertEqual(raccords['outer_bounds'],[0,2499])
            self.assertEqual([r['candidate_kept_decoded_frame'] for r in raccords['raccords']],[499,2125])
            presence=json.loads((root/'review/scan/report.json').read_text())
            self.assertEqual(presence['edge_mode'],'both')
            self.assertIn('contrast',presence['occurrences_by_hypothesis'])
            self.assertTrue((root/'review/raccords.tar.gz').is_file())
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
            with mock.patch('prepare_graphic_review.scan',side_effect=AssertionError('Full scan repeated')), \
                 mock.patch('prepare_graphic_review.export',side_effect=AssertionError('Native source extraction repeated')):
                resumed=run(source,[],0,2499,root/'retry',
                            observation_manifest=root/'review/observations/frame-map.json',cache_root=root)
            retry=json.loads(resumed.read_text())
            self.assertEqual(retry['status'],'ready_for_review')
            self.assertEqual(retry['reused_scan_from'],str(root/'review/scan/report.json'))
            self.assertEqual(retry['reused_review_from'],str(root/'review/raccords'))
            self.assertTrue((root/'retry/raccords.tar.gz').is_file())
            repeated=json.loads((root/'retry/raccords.json').read_text())
            self.assertEqual([r['candidate_kept_decoded_frame'] for r in repeated['raccords']],[499,2125])


if __name__=='__main__':unittest.main()
