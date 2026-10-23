"""Persist projects and enqueue through real child processes with literal paths."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from video_encoder_ui.trim_session import TrimSession, SourceReference, SegmentSelection
from video_encoder_ui.trim_project_bridge import TrimProjectBridge
from video_encoder_ui.trim_project_file_writer import TrimProjectFileWriter
from video_encoder_ui.trim_project_file_reader import TrimProjectFileReader
from video_encoder_ui.trim_export_queue_client import TrimExportQueueClient

NAMES = json.loads((Path(__file__).parents[2] / "spec/fixtures/path_names.json").read_text())


class SpecialCharacterPathsTest(unittest.TestCase):
    def test_save_reopen_enqueue_and_change_destination_with_literal_names(self):
        for name in NAMES:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                folder = root / name
                folder.mkdir()
                source = folder / (name + ".m2t")
                project = folder / (name + ".json")
                output = folder / (name + ".mkv")
                source.write_bytes(b"source must survive")
                bridge = folder / "bridge & conversion"
                bridge.write_text("#!/usr/bin/env python3\nimport sys,json\nd=json.load(sys.stdin);d.update(format='video_encoder.trim_project',version=2)\nfor item in d['timeline']:item['type']='segment'\nprint(json.dumps(d))\n")
                bridge.chmod(0o755)
                cli = folder / "queue : cli"
                capture = root / "arguments.json"
                cli.write_text("#!/usr/bin/env python3\nimport sys,json,os\nfrom pathlib import Path\n"
                               "Path(os.environ['ARGUMENT_CAPTURE']).write_text(json.dumps(sys.argv[1:]))\nprint('42')\n")
                cli.chmod(0o755)
                session = TrimSession()
                session.add_source(SourceReference("source", source))
                session.add_segment(SegmentSelection("source", 10, 100))
                writer = TrimProjectFileWriter(TrimProjectBridge(executable=bridge))
                writer.save(session, project)
                reopened = TrimProjectFileReader().load(project)
                self.assertEqual(reopened.sources[0].path, source)
                self.assertEqual(reopened.segments, session.segments)
                client = TrimExportQueueClient(executable=cli)
                with patch.dict(os.environ, ARGUMENT_CAPTURE=str(capture)):
                    self.assertEqual(client.enqueue(project, output), "42")
                    self.assertEqual(json.loads(capture.read_text()),
                                     ["enqueue-trim-export", str(project), "--output", str(output)])
                    client.set_output(42, output)
                    self.assertEqual(json.loads(capture.read_text()),
                                     ["set-job-output", "42", "--output", str(output)])
                self.assertEqual(source.read_bytes(), b"source must survive")
                self.assertFalse((root / "SHOULD_NOT_EXIST").exists())
