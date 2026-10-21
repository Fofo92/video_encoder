import hashlib
import io
from contextlib import redirect_stdout
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import numpy as np
from export_indexed_windows import source_identity
from prepare_overlay_review import plan,export,latest_report


class PrepareOverlayReviewTest(unittest.TestCase):
    def report(self):
        return {'status':'completed','sample_fps':5,'occurrences':[
            {'start_seconds':20.,'end_seconds_exclusive':21.},
            {'start_seconds':50.,'end_seconds_exclusive':51.},
            {'start_seconds':80.,'end_seconds_exclusive':81.}]}

    def test_plan_uses_group_endpoints_not_interior_graphic(self):
        groups,windows=plan(self.report(),10,100,radius=50)
        self.assertEqual(len(groups['groups']),1)
        self.assertEqual([w['candidate_role'] for w in windows],['departure','resume'])
        self.assertEqual([w['first_decoded_frame'] for w in windows],[450,1950])
        self.assertTrue(all(w['expected_frame_count']==100 for w in windows))
        self.assertTrue(all('reviewed_boundary_local_frame' not in w for w in windows))

    def test_unresolved_single_graphic_does_not_generate_an_extraction(self):
        report=self.report();report['occurrences']=report['occurrences'][:1]
        with self.assertRaises(ValueError):plan(report,10,100)

    def test_changed_source_identity_rejects_before_creating_output(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.mkv';source.write_bytes(b'old')
            r=self.report();r.update(source=str(source),source_identity=source_identity(source))
            source.write_bytes(b'changed')
            path=root/'report.json';path.write_text(json.dumps(r))
            with self.assertRaisesRegex(ValueError,'identity differs'):export(path,10,100,root/'output',radius=50)
            self.assertFalse((root/'output').exists())

    def test_latest_report_ignores_newer_failed_or_wrong_identity_reports(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.mkv';source.write_bytes(b'source')
            r=self.report();r.update(source=str(source.resolve()),source_identity=source_identity(source))
            for folder,changes in [('good',{}),('failed',{'status':'failed'}),('wrong',{'source_identity':{}})]:
                path=root/folder;path.mkdir();(path/'report.json').write_text(json.dumps({**r,**changes}))
            self.assertEqual(latest_report(root,source),root/'good/report.json')
            source.write_bytes(b'new source')
            with self.assertRaisesRegex(ValueError,'No completed'):latest_report(root,source)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg unavailable')
    def test_real_export_preserves_native_counter_phase_and_source_bytes(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);source=root/'source.mkv'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',
                            "nullsrc=s=160x90:r=25,geq=lum='mod(N,220)+16':cb=128:cr=128",
                            '-t','110','-c:v','ffv1',str(source)],check=True)
            original=hashlib.sha256(source.read_bytes()).hexdigest()
            report=self.report();report['occurrences'][-1].update(start_seconds=104.4,end_seconds_exclusive=105.4)
            report.update(source=str(source),source_identity=source_identity(source))
            path=root/'report.json';path.write_text(json.dumps(report))
            progress=io.StringIO()
            with redirect_stdout(progress):archive=export(path,10,109,root/'review',radius=50)
            self.assertIn('source frame 2500',progress.getvalue())
            self.assertTrue(archive.is_file())
            m=json.loads((root/'review/frame-map.json').read_text())
            self.assertEqual(m['status'],'export_complete_editor_alignment_unverified')
            self.assertFalse(m['reviewed_interior_cuts_used'])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),original)
            raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(root/'review/resume-1.mp4'),
                                         '-vf','scale=1:1','-pix_fmt','rgb24','-f','rawvideo','-'])
            values=np.frombuffer(raw,dtype=np.uint8).reshape(-1,3).mean(axis=1)
            self.assertEqual(len(values),100)
            # Source frames 2560..2659: the brightness counter wraps at 2640,
            # exactly observation frame 80, despite original timestamps.
            self.assertEqual((np.flatnonzero(np.diff(values)<-100)+1).tolist(),[80])


if __name__=='__main__':unittest.main()
