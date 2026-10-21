import json
import hashlib
from pathlib import Path
import tarfile
import tempfile
import unittest
from collect_graphic_diagnostics import collect


class CollectGraphicDiagnosticsTest(unittest.TestCase):
    def test_format_route_collects_native_clips_without_unused_observations(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);pipeline=self.clip_fixture(root)
            pipeline.pop('observation_manifest');pipeline.pop('observation_manifest_sha256')
            pipeline['preparation_method']='format_hypotheses'
            (root/'run/pipeline.json').write_text(json.dumps(pipeline))
            output=collect(root,'/source.m2t',root/'out.tar.gz',include_review_clips=True)
            with tarfile.open(output) as archive:
                names=archive.getnames()
                self.assertEqual(sum(name.endswith('.mp4') for name in names),2)
                self.assertFalse(any('/observations/' in name for name in names))

    def test_sealed_discovery_cache_is_collected_without_original_recording(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);pipeline=self.clip_fixture(root)
            directory=root/'discovery';directory.mkdir()
            cache=directory/'sampled-rgb.bin';cache.write_bytes(b'x'*(20*1728))
            manifest={'status':'completed','source':pipeline['source'],
                      'source_identity':pipeline['source_identity'],'sampled_frames':20,
                      'cache_path':str(cache),'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest()}
            (directory/'manifest.json').write_text(json.dumps(manifest))
            output=collect(root,'/source.m2t',root/'out.tar.gz',include_discovery_cache=True)
            with tarfile.open(output) as archive:
                self.assertEqual(archive.extractfile('graphic-diagnostics/discovery-cache/sampled-rgb.bin').read(),cache.read_bytes())
                index=json.load(archive.extractfile('graphic-diagnostics/collection.json'))
                self.assertTrue(index['existing_discovery_cache_included'])
                self.assertFalse(index['recording_opened'])
            cache.write_bytes(b'y'*(20*1728))
            with self.assertRaisesRegex(ValueError,'Aucun cache'):
                collect(root,'/source.m2t',root/'tampered.tar.gz',include_discovery_cache=True)
            self.assertFalse((root/'tampered.tar.gz').exists())

    def test_foreign_cache_identity_and_escaped_cache_path_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);pipeline=self.clip_fixture(root)
            cache=root/'sampled-rgb.bin';cache.write_bytes(b'x'*1728)
            manifest={'status':'completed','source':pipeline['source'],'source_identity':{'bytes':999},
                      'sampled_frames':1,'cache_path':str(cache),'cache_sha256':hashlib.sha256(cache.read_bytes()).hexdigest()}
            path=root/'manifest.json';path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                collect(root,'/source.m2t',root/'foreign.tar.gz',include_discovery_cache=True)
            manifest.update(source_identity=pipeline['source_identity'],cache_path='/outside/cache.bin')
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                collect(root,'/source.m2t',root/'outside.tar.gz',include_discovery_cache=True)

    def clip_fixture(self, root):
        run = root / 'run'; run.mkdir()
        pipeline = {'source': '/source.m2t', 'source_identity': {'bytes': 1000}}
        for field, name in [('observation_manifest', 'old-observations'), ('review_manifest', 'native')]:
            directory = root / name; directory.mkdir()
            windows = []
            for number in range(2):
                clip = directory / f'clip-{number}.mp4'; clip.write_bytes(b'known clip')
                windows.append({'name': clip.name, 'sha256': hashlib.sha256(clip.read_bytes()).hexdigest()})
            manifest = directory / 'frame-map.json'
            manifest.write_text(json.dumps({'source': pipeline['source'],
                'source_identity': pipeline['source_identity'], 'windows': windows}))
            pipeline[field] = str(manifest)
            pipeline[field + '_sha256'] = hashlib.sha256(manifest.read_bytes()).hexdigest()
        (run / 'pipeline.json').write_text(json.dumps(pipeline))
        return pipeline

    def test_explicit_clip_collection_uses_verified_manifests_including_previous_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); self.clip_fixture(root)
            (root / 'old-observations/unrelated.mkv').write_bytes(b'never include')
            output = collect(root, '/source.m2t', root / 'out.tar.gz', True)
            with tarfile.open(output) as archive:
                names = archive.getnames()
                self.assertEqual(sum(name.endswith('.mp4') for name in names), 4)
                self.assertFalse(any(name.endswith('.mkv') for name in names))
                index = json.load(archive.extractfile('graphic-diagnostics/collection.json'))
                self.assertTrue(index['existing_review_clips_included'])
                self.assertFalse(index['recording_opened'])

    def test_changed_clip_or_manifest_rejects_archive_before_creation(self):
        for changed in ['clip', 'manifest', 'outside']:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary); pipeline = self.clip_fixture(root)
                if changed == 'clip':
                    (root / 'native/clip-0.mp4').write_bytes(b'changed')
                elif changed == 'manifest':
                    (root / 'native/frame-map.json').write_text('{}')
                else:
                    pipeline['review_manifest'] = '/outside/frame-map.json'
                    (root / 'run/pipeline.json').write_text(json.dumps(pipeline))
                with self.assertRaises((ValueError, FileNotFoundError)):
                    collect(root, '/source.m2t', root / 'out.tar.gz', True)
                self.assertFalse((root / 'out.tar.gz').exists())

    def test_collects_nested_reports_without_source_or_videos(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / 'run'
            (run / 'scan').mkdir(parents=True)
            source = '/recording/need-not-exist.m2t'
            (run / 'pipeline.json').write_text(json.dumps({'source': source}))
            (run / 'scan/report.json').write_text('{"status":"completed"}')
            (run / 'video.mkv').write_bytes(b'never include')
            output = collect(root, source, root / 'diagnostics.tar.gz')
            with tarfile.open(output) as archive:
                self.assertEqual(set(archive.getnames()), {
                    'graphic-diagnostics/pipeline.json', 'graphic-diagnostics/scan/report.json',
                    'graphic-diagnostics/collection.json'})
                index = json.load(archive.extractfile('graphic-diagnostics/collection.json'))
                self.assertFalse(index['recording_opened'])
                self.assertFalse(index['calculation_started'])
            with self.assertRaises(FileExistsError):
                collect(root, source, output)

    def test_missing_source_report_does_not_start_calculation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'pipeline.json').write_text('[]')
            with self.assertRaises(ValueError):
                collect(root, '/missing.m2t', root / 'out.tar.gz')
            self.assertFalse((root / 'out.tar.gz').exists())

    def test_symlink_and_oversized_reports_are_not_packaged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run = root / 'run'; run.mkdir()
            (run / 'pipeline.json').write_text('{"source":"/source.m2t"}')
            foreign = root / 'foreign.json'; foreign.write_text('private')
            link = run / 'escape.json'; link.symlink_to(foreign)
            with self.assertRaises(ValueError):
                collect(root, '/source.m2t', root / 'out.tar.gz')
            link.unlink()
            (run / 'huge.log').write_bytes(b'x' * (2 * 1024 * 1024 + 1))
            with self.assertRaises(ValueError):
                collect(root, '/source.m2t', root / 'out.tar.gz')
            self.assertFalse((root / 'out.tar.gz').exists())


if __name__ == '__main__':
    unittest.main()
