import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

from video_encoder_ui.copy_version import enqueue, pipeline, suggested_output


class CopyVersionTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "Film avec espaces.mkv"
        self.source.write_bytes(b"source")
        self.details = {"streams": [
            {"index": 0, "codec_type": "video"},
            {"index": 1, "codec_type": "audio", "tags": {"language": "fra"}},
            {"index": 2, "codec_type": "audio", "tags": {"language": "qaa"}}]}

    def document(self):
        return pipeline().prepare(self.source, 2, original_confirmed=True,
                                  burned_french_confirmed=True, details=self.details)

    def test_original_audio_and_burned_subtitles_require_separate_explicit_confirmation(self):
        for original, burned in [(False, True), (True, False), (False, False)]:
            with self.assertRaises(ValueError):
                pipeline().prepare(self.source, 2, original_confirmed=original,
                                   burned_french_confirmed=burned, details=self.details)

    def test_qaas_presence_does_not_confirm_original_audio_and_any_chosen_index_must_be_audio(self):
        with self.assertRaises(ValueError):
            pipeline().prepare(self.source, 0, original_confirmed=True,
                               burned_french_confirmed=True, details=self.details)
        document = self.document()
        self.assertEqual(document["version_change"]["audio_index"], 2)
        self.assertTrue(document["version_change"]["original_confirmed"])
        self.assertEqual(document["version_change"]["identity"], pipeline().identity(self.source))

    def test_saving_and_enqueuing_does_not_run_a_worker_or_overwrite_the_source(self):
        queue = Mock()
        output = self.source.with_name("Film - VOST.mkv")
        enqueue(self.document(), output, queue)
        saved = json.loads(output.with_suffix(".json").read_text())
        self.assertEqual(saved["sources"][0]["path"], str(self.source))
        queue.enqueue.assert_called_once_with(output.with_suffix(".json"), output)
        queue.start.assert_not_called()
        self.assertEqual(self.source.read_bytes(), b"source")
        with self.assertRaises(FileExistsError):
            enqueue(self.document(), output, queue)
        self.assertEqual(queue.enqueue.call_count, 1)

    def test_vidb_hint_uses_the_confirmed_profile_without_guessing_from_missing_subtitles(self):
        from video_encoder_ui.planned_language import identification_language
        inspector = Mock()
        inspector.inspect.side_effect = AssertionError("No implicit track guessing")
        self.assertEqual(identification_language(self.document(), inspector), "VOST")
        inspector.inspect.assert_not_called()

    def test_existing_destinations_and_symlinks_are_never_replaced(self):
        queue = Mock()
        output = self.source.with_name("VOST.mkv")
        output.write_bytes(b"keep")
        with self.assertRaises(ValueError):
            enqueue(self.document(), output, queue)
        self.assertEqual(output.read_bytes(), b"keep")
        output.unlink()
        output.symlink_to(self.source.with_name("absent.mkv"))
        with self.assertRaises(ValueError):
            enqueue(self.document(), output, queue)
        queue.enqueue.assert_not_called()

    def test_a_failed_enqueue_keeps_a_retryable_project_and_suggestion_avoids_existing_names(self):
        output = suggested_output(self.source)
        queue = Mock()
        queue.enqueue.side_effect = RuntimeError("queue unavailable")
        with self.assertRaises(RuntimeError):
            enqueue(self.document(), output, queue)
        self.assertTrue(output.with_suffix(".json").is_file())
        self.assertNotEqual(output, suggested_output(self.source))


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg unavailable")
class CopyVersionPipelineTest(unittest.TestCase):
    def test_real_remux_preserves_video_and_selected_audio_and_refuses_replacement(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "Copie VM.mkv"
            subprocess.run([
                "ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i",
                "color=blue:s=64x64:r=5,drawbox=x=2:y=50:w=60:h=10:color=white:t=fill",
                "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
                "-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000",
                "-t", "1", "-map", "0:v", "-map", "1:a", "-map", "2:a",
                "-c:v", "mpeg4", "-c:a", "aac", "-metadata:s:a:0", "language=fra",
                "-metadata:s:a:1", "language=qaa", str(source)], check=True)
            original = source.read_bytes()
            module = pipeline()
            document = module.prepare(source, 2, original_confirmed=True, burned_french_confirmed=True)
            project = root / "Copie VOST.json"
            project.write_text(json.dumps(document))
            output = root / "Copie VOST.mkv"
            workspace = root / "workspace"
            module.export(project, output, workspace)
            streams = module.probe(output)["streams"]
            self.assertEqual([row["codec_type"] for row in streams], ["video", "audio"])
            self.assertEqual(streams[1]["tags"]["language"], "qaa")
            self.assertEqual(streams[1]["disposition"]["default"], 1)
            self.assertEqual(source.read_bytes(), original)
            for source_index, target_index in [(0, 0), (2, 1)]:
                def packet_hash(path, index):
                    data = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path),
                                                    "-map", f"0:{index}", "-c", "copy", "-f", "data", "-"])
                    return hashlib.sha256(data).hexdigest()
                self.assertEqual(packet_hash(source, source_index), packet_hash(output, target_index))
            finished = output.read_bytes()
            with self.assertRaises(FileExistsError):
                module.export(project, output, workspace)
            self.assertEqual(output.read_bytes(), finished)
            source.write_bytes(original + b"changed")
            with self.assertRaises(ValueError):
                module.export(project, root / "Other.mkv", workspace)
            self.assertFalse((root / "Other.mkv").exists())
