import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_encoder_ui.dvd_import import audio_defaults, new_project, provisional_output, subtitle_default, write_new

MODULE = Path(__file__).resolve().parents[2] / 'lib/video_encoder/dvd_pipeline.py'
spec = importlib.util.spec_from_file_location('dvd_pipeline', MODULE)
dvd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dvd)


def probe():
    return {'format': {'duration': '2700'}, 'streams': [
        {'index': 0, 'codec_type': 'video', 'codec_name': 'mpeg2video', 'avg_frame_rate': '25/1'},
        {'index': 1, 'codec_type': 'audio', 'codec_name': 'ac3', 'tags': {'language': 'fra'}},
        {'index': 2, 'codec_type': 'audio', 'codec_name': 'ac3', 'tags': {'language': 'eng'}},
        {'index': 3, 'codec_type': 'subtitle', 'codec_name': 'dvd_subtitle',
         'tags': {'language': 'fra'}, 'nb_read_packets': '4'},
        {'index': 4, 'codec_type': 'subtitle', 'codec_name': 'dvd_subtitle',
         'tags': {'language': 'fra'}, 'nb_read_packets': '568'}]}


class DvdPipelineTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "L'été & l'hiver.mkv"
        self.source.write_bytes(b'local source')
        self.copied = {'path': str(self.source), 'signature': dvd.signature(self.source), 'probe': probe(),
                       'duration': 2700, 'dvd_title': 2}
        self.document = new_project(self.copied, [{'index': 1, 'role': 'french'}, {'index': 2, 'role': 'original'}], [4])
        self.document['vidb'] = {'status': 'identified', 'project_id': self.document['project_id'],
                                 'record_id': 42, 'binding_token': 'test-binding'}
        self.project = self.root / 'episode.json'
        self.project.write_text(json.dumps(self.document), encoding='utf-8')
        self.output = self.root / "S02 E01 - L'été & l'hiver.mkv"

    def final_probe(self):
        result = probe()
        result['streams'] = result['streams'][:3] + [result['streams'][4]]
        return result

    def encode(self, command, **_kwargs):
        if command[0] == 'HandBrakeCLI':
            Path(command[command.index('--output') + 1]).write_bytes(b'encoded')
        else:
            Path(command[-1]).write_bytes(b'final')

    def test_exports_local_copy_and_passes_second_subtitle_without_handbrake_decoding(self):
        with patch.object(dvd, 'inspect', side_effect=[probe(), self.final_probe()]), \
                patch.object(dvd, 'run', side_effect=self.encode) as runner:
            dvd.export(self.project, self.output, self.root / 'workspace')
        commands = [call.args[0] for call in runner.call_args_list]
        handbrake, remux = commands
        self.assertIn(str(self.source), list(map(str, handbrake)))
        self.assertNotIn('/dev/sr0', str(commands))
        self.assertEqual('none', handbrake[handbrake.index('--subtitle') + 1])
        self.assertEqual('1,2', handbrake[handbrake.index('--audio') + 1])
        self.assertIn('1:4', remux)
        self.assertNotIn('1:3', remux)
        self.assertEqual('copy', remux[remux.index('-c') + 1])
        self.assertIn('language=eng', remux)
        self.assertEqual(b'final', self.output.read_bytes())
        self.assertTrue(self.source.exists())

    def test_audio_ordinals_follow_selected_stream_not_assumed_language_position(self):
        selected, _ = dvd.select_tracks(self.document, probe())
        self.assertEqual([1, 2], [number for number, _ in selected])
        self.document['dvd']['audio'] = [{'index': 2, 'role': 'original'}]
        selected, _ = dvd.select_tracks(self.document, probe())
        self.assertEqual(2, selected[0][0])

    def test_failed_encoder_can_be_retried_without_output_or_source_loss(self):
        with patch.object(dvd, 'inspect', return_value=probe()), patch.object(dvd, 'run', side_effect=OSError('failed')):
            with self.assertRaises(OSError):
                dvd.export(self.project, self.output, self.root / 'workspace')
        self.assertFalse(self.output.exists())
        self.assertTrue(self.source.exists())
        self.assertEqual([], list((self.root / 'workspace').iterdir()))
        self.test_exports_local_copy_and_passes_second_subtitle_without_handbrake_decoding()

    def test_bad_final_streams_are_not_published(self):
        with patch.object(dvd, 'inspect', side_effect=[probe(), probe()]), \
                patch.object(dvd, 'run', side_effect=self.encode):
            with self.assertRaisesRegex(ValueError, 'pistes finales'):
                dvd.export(self.project, self.output, self.root / 'workspace')
        self.assertFalse(self.output.exists())

    def test_refuses_modified_source_or_unbound_project(self):
        self.source.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'copie locale'):
            dvd.load_project(self.project)
        self.document['dvd']['signature'] = dvd.signature(self.source)
        self.document.pop('vidb')
        self.project.write_text(json.dumps(self.document), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'vidb'):
            dvd.load_project(self.project)

    def test_refuses_existing_and_broken_symlink_outputs(self):
        self.output.symlink_to(self.root / 'missing')
        with self.assertRaisesRegex(ValueError, 'déjà présente'):
            dvd.export(self.project, self.output, self.root / 'workspace')
        with self.assertRaises(FileExistsError):
            dvd.publish(self.source, self.output)
        self.assertTrue(self.source.exists())

    def test_copy_checks_duration_and_keeps_drive_out_of_persistent_source(self):
        def copier(command, **_kwargs):
            Path(command[-1]).write_bytes(b'dvd copy')
        with patch.object(dvd, 'run', side_effect=copier), patch.object(dvd, 'inspect', return_value=probe()):
            copied = dvd.copy_title('/dev/sr0', 2, self.root / 'copy', 2700)
        self.assertNotIn('/dev/', copied['path'])
        self.assertEqual(2, copied['dvd_title'])
        self.assertEqual(dvd.signature(copied['path']), copied['signature'])
        with patch.object(dvd, 'run', side_effect=copier), patch.object(dvd, 'inspect', return_value=probe()):
            with self.assertRaisesRegex(ValueError, 'durée'):
                dvd.copy_title('/dev/sr0', 3, self.root / 'copy', 1000)
        self.assertFalse((self.root / 'copy/titre-03.mkv').exists())

    def test_scan_parses_title_json_with_trailing_handbrake_output(self):
        raw = {'TitleList': [{'Index': 2, 'Duration': {'Ticks': 2700 * 90000}}]}
        with patch.object(dvd, 'run', return_value='Progress\nJSON Title Set: ' + json.dumps(raw) + '\nDone'):
            self.assertEqual(2700, dvd.scan('/dev/sr0')[0]['duration'])

    def test_ambiguous_audio_is_not_silently_assigned_a_language_role(self):
        rows = dvd.streams(probe(), 'audio')
        self.assertEqual((1, 2), audio_defaults(rows))
        rows.append({'index': 9, 'tags': {'language': 'deu'}})
        self.assertEqual((1, None), audio_defaults(rows))
        rows[-1]['disposition'] = {'visual_impaired': 1}
        self.assertEqual((1, 2), audio_defaults(rows))
        self.assertEqual(4, subtitle_default(dvd.streams(probe(), 'subtitle')))

    def test_rejects_duplicates_and_incorrect_track_types(self):
        self.document['dvd']['subtitles'] = [1]
        with self.assertRaisesRegex(ValueError, 'sous-titres'):
            dvd.select_tracks(self.document, probe())
        self.document['dvd']['subtitles'] = []
        self.document['dvd']['audio'][1]['index'] = 1
        with self.assertRaisesRegex(ValueError, 'deux fois'):
            dvd.select_tracks(self.document, probe())

    def test_exclusive_project_save_keeps_original(self):
        with self.assertRaises(FileExistsError):
            write_new(self.project, {'overwrite': True})
        self.assertEqual(self.document, json.loads(self.project.read_text()))
        output = provisional_output('Code/Quantum', True, 2, 1)
        self.assertEqual(Path('/videos/Code_Quantum - S02 E01.mkv'), output)

    def test_non_pal_is_refused_before_encoding(self):
        data = probe()
        data['streams'][0]['avg_frame_rate'] = '30000/1001'
        with patch.object(dvd, 'inspect', return_value=data), patch.object(dvd, 'run') as runner:
            with self.assertRaisesRegex(ValueError, 'PAL'):
                dvd.export(self.project, self.output, self.root / 'workspace')
        runner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
