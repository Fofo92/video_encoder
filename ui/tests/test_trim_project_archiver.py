import unittest
from pathlib import Path
from unittest.mock import Mock

from video_encoder_ui.trim_project_archiver import (
    TrimProjectArchiver,
)


class TrimProjectArchiverTest(unittest.TestCase):
    def test_copies_the_project_next_to_the_output(self):
        copy_file = Mock()
        archiver = TrimProjectArchiver(
            copy_file=copy_file
        )

        destination = archiver.archive(
            "/projects/movie.json",
            "/videos/movie.mkv"
        )

        copy_file.assert_called_once_with(
            Path("/projects/movie.json"),
            Path("/videos/movie.json")
        )
        self.assertEqual(
            destination,
            Path("/videos/movie.json")
        )

    def test_keeps_an_already_adjacent_project(self):
        copy_file = Mock()
        archiver = TrimProjectArchiver(
            copy_file=copy_file
        )

        destination = archiver.archive(
            "/videos/movie.json",
            "/videos/movie.mkv"
        )

        copy_file.assert_not_called()
        self.assertEqual(
            destination,
            Path("/videos/movie.json")
        )


if __name__ == "__main__":
    unittest.main()
