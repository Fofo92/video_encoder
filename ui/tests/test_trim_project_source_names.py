import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.trim_project_source_names import (
    TrimProjectSourceNames,
)


class TrimProjectSourceNamesTest(unittest.TestCase):
    def test_returns_the_source_file_names(self):
        reader = Mock()
        reader.load.return_value = SimpleNamespace(
            sources=(
                SimpleNamespace(
                    path=Path("/commun/source-a.m2t")
                ),
                SimpleNamespace(
                    path=Path("/commun/source-b.m2t")
                ),
            )
        )
        source_names = TrimProjectSourceNames(
            reader=reader
        )

        with tempfile.TemporaryDirectory() as directory:
            project_path = Path(directory) / "movie.json"
            project_path.write_text(
                json.dumps({"version": 2}),
                encoding="utf-8",
            )

            self.assertEqual(
                source_names(project_path),
                "source-a.m2t · source-b.m2t",
            )

    def test_caches_names_while_the_project_is_unchanged(self):
        reader = Mock()
        reader.load.return_value = SimpleNamespace(
            sources=(
                SimpleNamespace(
                    path=Path("/commun/source.m2t")
                ),
            )
        )
        source_names = TrimProjectSourceNames(
            reader=reader
        )

        with tempfile.TemporaryDirectory() as directory:
            project_path = Path(directory) / "movie.json"
            project_path.write_text(
                "{}",
                encoding="utf-8",
            )

            source_names(project_path)
            source_names(project_path)

        reader.load.assert_called_once_with(
            project_path
        )

    def test_reports_an_unavailable_project(self):
        source_names = TrimProjectSourceNames()

        self.assertEqual(
            source_names("/missing/movie.json"),
            "Projet indisponible",
        )


if __name__ == "__main__":
    unittest.main()
