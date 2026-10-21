import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
from prepare_graphic_review import run
from export_indexed_windows import source_identity


class PrepareGraphicReviewTest(unittest.TestCase):
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
            observations=[]
            for index,start in enumerate([18,81]):
                clip=root/f'observation-{index}.mkv'
                subprocess.run(['ffmpeg','-v','error','-ss',str(start),'-i',str(source),'-t','6',
                                '-an','-c:v','ffv1',str(clip)],check=True)
                observations.append(clip)
            teacher=root/'observations.json'
            teacher.write_text(json.dumps({'source':str(source),'source_identity':source_identity(source),
                                           'outer_bounds':[0,2499],
                                           'windows':[{'name':clip.name,'first_decoded_frame':start*25,
                                                       'end_decoded_frame_exclusive':(start+6)*25}
                                                      for clip,start in zip(observations,[18,81])]}))
            report_path=run(source,[],0,2499,root/'review',observation_manifest=teacher)
            report=json.loads(report_path.read_text())
            self.assertEqual(report['status'],'ready_for_review', (root/'review/raccords.json').read_text())
            self.assertTrue(report['needs_manual_review'])
            self.assertEqual(report['observation_manifest_sha256'],hashlib.sha256(teacher.read_bytes()).hexdigest())
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


if __name__=='__main__':unittest.main()
