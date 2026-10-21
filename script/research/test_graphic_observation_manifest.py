import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from export_indexed_windows import source_identity
from graphic_observation_manifest import observations_from_manifest


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg unavailable')
class GraphicObservationManifestTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.source=self.root/'source.m2t';self.source.write_bytes(b'original')
        clip=self.root/'one.mkv'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=gray:s=32x18:r=25:d=1',
                        '-c:v','ffv1',str(clip)],check=True)
        (self.root/'two.mkv').write_bytes(clip.read_bytes())
        self.data={'source':str(self.source),'source_identity':source_identity(self.source),'outer_bounds':[0,999],
                   'windows':[{'name':name,'first_decoded_frame':first,'end_decoded_frame_exclusive':first+25,
                               'sha256':hashlib.sha256(clip.read_bytes()).hexdigest()}
                              for name,first in [('one.mkv',100),('two.mkv',200)]]}
        self.manifest=self.root/'manifest.json';self.save()

    def save(self):self.manifest.write_text(json.dumps(self.data))

    def test_complete_clips_are_reusable_after_exterior_bound_adjustment(self):
        paths,digest=observations_from_manifest(self.manifest,self.source,(70,240))
        self.assertEqual([p.name for p in paths],['one.mkv','two.mkv'])
        self.assertEqual(digest,hashlib.sha256(self.manifest.read_bytes()).hexdigest())
        with self.assertRaises(ValueError):observations_from_manifest(self.manifest,self.source,(110,240))
        self.source.write_bytes(b'manual change')
        with self.assertRaises(ValueError):observations_from_manifest(self.manifest,self.source,(70,240))

    def test_truncated_count_is_rejected_before_learning(self):
        self.data['windows'][0]['end_decoded_frame_exclusive']=126;self.save()
        with self.assertRaisesRegex(ValueError,'truncated'):
            observations_from_manifest(self.manifest,self.source,(0,999))

    def test_changed_checksum_and_escaping_path_are_rejected(self):
        self.data['windows'][0]['sha256']='wrong';self.save()
        with self.assertRaisesRegex(ValueError,'checksum'):
            observations_from_manifest(self.manifest,self.source,(0,999))
        self.data['windows'][0]['name']='../one.mkv';self.save()
        with self.assertRaisesRegex(ValueError,'local'):
            observations_from_manifest(self.manifest,self.source,(0,999))


if __name__=='__main__':unittest.main()
