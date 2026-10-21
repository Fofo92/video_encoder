import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from collect_graphic_diagnostics import collect


class CollectGraphicDiagnosticsTest(unittest.TestCase):
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
