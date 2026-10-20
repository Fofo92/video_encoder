import shutil
import json
from unittest import mock
import subprocess
import tempfile
from pathlib import Path
import unittest
import numpy as np
from scan_stable_overlays import learn_model, scan_blocks, padded_crop, rgb_blocks, run
from stable_overlay_signals import presence_scores


class ScanStableOverlaysTest(unittest.TestCase):
    def model(self):
        clips=[]
        for seed in range(3):
            a=np.random.default_rng(seed).integers(0,150,(20,40,64,3),dtype=np.uint8)
            a[6:13,20:32,40:44]=255;a[6:13,28:32,40:54]=255
            clips.append(a)
        return learn_model(clips)

    def test_presence_crosses_block_boundaries_and_short_tail_is_not_duplicated(self):
        model=self.model()
        source=np.zeros((23,40,64,3),dtype=np.uint8)
        source[9:16,20:32,40:44]=255;source[9:16,28:32,40:54]=255
        source[22:,20:32,40:44]=255;source[22:,28:32,40:54]=255
        x,y,w,h=model['crop'];crop=source[:,y:y+h,x:x+w]
        progress=[]
        count,intervals=scan_blocks(iter([crop[:11],crop[11:13],crop[13:17],crop[17:21],crop[21:]]),model,progress.append)
        self.assertEqual(count,23)
        self.assertEqual([(row['first_sample'],row['end_sample_exclusive']) for row in intervals],[(9,16)])
        self.assertEqual(progress[-1],23)

    def test_padding_preserves_edge_scores_of_the_full_frame(self):
        model=self.model();x,y,w,h=model['crop']
        a=np.random.default_rng(11).integers(0,256,(10,40,64,3),dtype=np.uint8)
        globalmask=np.zeros((40,64),dtype=bool);globalmask[y:y+h,x:x+w]=model['mask']
        lx,ly,lw,lh=model['bbox']
        full=presence_scores(a,globalmask,[x+lx,y+ly,lw,lh])
        cropped=presence_scores(a[:,y:y+h,x:x+w],model['mask'],model['bbox'])
        np.testing.assert_array_equal(full,cropped)

    def test_empty_stream_has_no_occurrences(self):
        self.assertEqual(scan_blocks(iter([]),self.model()),(0,[]))

    def test_wrong_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            scan_blocks(iter([np.zeros((10,12,12,3),dtype=np.uint8)]),self.model())

    def test_failure_and_interrupt_leave_explicit_reports(self):
        for error,status in [(ValueError('bad stream'),'failed'),(KeyboardInterrupt(),'interrupted')]:
            with self.subTest(status=status), tempfile.TemporaryDirectory() as name:
                root=Path(name);source=root/'source.mkv';source.write_bytes(b'source')
                clips=[root/'one.mp4',root/'two.mp4']
                for clip in clips:clip.write_bytes(b'observation')
                with mock.patch('scan_stable_overlays.verify_aspect',side_effect=error):
                    with self.assertRaises(type(error)):run(source,clips,root/'output')
                report=json.loads((root/'output/report.json').read_text())
                self.assertEqual(report['status'],status)
                self.assertEqual(source.read_bytes(),b'source')
                self.assertNotIn('occurrences',report)

    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg unavailable')
    def test_real_decoder_preserves_odd_crop_coordinates_and_short_last_block(self):
        with tempfile.TemporaryDirectory() as name:
            directory=Path(name);source=directory/'source.mkv'
            a=np.zeros((8,360,640,3),dtype=np.uint8)
            a[:,:,3:20,0]=190
            a[:,:20,:,1]=110
            for j in range(8):a[j,:,:,2]=j*20
            subprocess.run(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','640x360',
                            '-r','5','-i','pipe:0','-c:v','ffv1','-pix_fmt','bgr0',str(source)],
                           input=a.tobytes(),check=True)
            blocks=list(rgb_blocks(source,directory/'decode.log',crop=[3,7,32,16],max_frames=20,block_frames=5))
            self.assertEqual([len(block) for block in blocks],[5,3])
            np.testing.assert_array_equal(np.concatenate(blocks),a[:,7:23,3:35])
            with self.assertRaisesRegex(ValueError,'sampling limit'):
                list(rgb_blocks(source,directory/'limit.log',crop=[3,7,32,16],max_frames=5,block_frames=5))


if __name__=='__main__':unittest.main()
