import tempfile
import unittest
from pathlib import Path

from video_encoder_ui.trim_project_archiver import TrimProjectArchiver


class ArchiverConflictTest(unittest.TestCase):
    def test_does_not_overwrite_a_different_existing_project(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            destination = Path(directory) / "output.json"
            source.write_text("source")
            destination.write_text("existing")
            with self.assertRaises(FileExistsError):
                TrimProjectArchiver().archive(source, destination.with_suffix(".mkv"))
            self.assertEqual(destination.read_text(), "existing")

    def test_reuses_an_identical_project_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            destination = Path(directory) / "output.json"
            source.write_text("same")
            destination.write_text("same")
            previous = destination.stat().st_mtime_ns
            result = TrimProjectArchiver().archive(source, destination.with_suffix(".mkv"))
            self.assertEqual(result, destination)
            self.assertEqual(destination.stat().st_mtime_ns, previous)


if __name__ == "__main__":
    unittest.main()
