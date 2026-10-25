import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    import PySide6
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui import catalogue_destination as destination
from video_encoder_ui.vidb_project_link import VidbProjectLink


class DocumentaryDestinationTest(unittest.TestCase):
    def test_known_documentary_uses_documentary_root_without_a_film_genre_directory(self):
        result = destination.suggested_film_output(
            {"french_title": "Les glaces", "genres": ["Documentaire"]}, Path("/videos/capture.mkv"))
        self.assertEqual(result, Path("/videos/Documentaires/Les glaces.mkv"))

    def test_documentary_source_gives_context_even_without_external_identification(self):
        self.assertEqual(destination.documentary_fallback(
            Path("/videos/Les glaces.json"), Path("/videos/Documentaires/source.m2t")),
            Path("/videos/Documentaires/Les glaces.json"))

    def test_unknown_capture_is_not_silently_classified_as_a_documentary(self):
        path = Path("/videos/capture.json")
        self.assertEqual(destination.documentary_fallback(path, Path("/commun/to_be_cut/capture.m2t")), path)

    def test_an_explicit_destination_is_preserved(self):
        path = Path("/videos/Documentaires/Saison 01/Les glaces.json")
        self.assertEqual(destination.documentary_fallback(path), path)

    def test_manual_destination_keeps_the_directory_from_the_record_genre(self):
        dialog = Mock()
        buttons = [Mock(), Mock(), Mock()]
        dialog.addButton.side_effect = buttons
        dialog.clickedButton.return_value = buttons[1]
        with patch.object(destination.QtWidgets, "QMessageBox", return_value=dialog):
            result = destination.confirm_destination(None,
                {"french_title": "Les glaces", "genres": ["Documentaire"]}, Path("/videos/capture.json"))
        self.assertEqual(result, Path("/videos/Documentaires/Les glaces.mkv"))

    def test_manual_destination_keeps_the_directory_for_a_film_too(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Drame").mkdir()
            metadata = {"french_title": "Film", "genres": ["Drame"]}
            proposed = destination.suggested_film_output(metadata, Path("/videos/capture.json"), root)
            dialog = Mock()
            buttons = [Mock(), Mock(), Mock()]
            dialog.addButton.side_effect = buttons
            dialog.clickedButton.return_value = buttons[1]
            with patch.object(destination, "suggested_film_output", return_value=proposed), \
                 patch.object(destination.QtWidgets, "QMessageBox", return_value=dialog):
                result = destination.confirm_destination(None, metadata, Path("/videos/capture.json"))
            self.assertEqual(result.parent, root / "Drame")

    def test_manual_record_metadata_without_external_source_reaches_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "vidb.json"
            config.write_text(json.dumps({"url": "https://vidb.test", "token": "a" * 64}))
            def transport(_config, payload):
                return {"status": "identified", "binding": {"project_id": payload["project"]["project_id"],
                        "record_id": 123, "binding_token": "signed"},
                        "metadata": {"french_title": "Les glaces", "record_kind": "standalone_video",
                                     "genres": ["Documentaire"], "year": None, "abstract": ""}}
            writer = SimpleNamespace(vidb_link=VidbProjectLink(config, transport=transport))
            source = Path("/commun/to_be_cut/Les glaces.m2t")
            session = SimpleNamespace(sources=[SimpleNamespace(path=source)])
            dialog = Mock()
            buttons = [Mock(), Mock(), Mock()]
            dialog.addButton.side_effect = buttons
            dialog.clickedButton.return_value = buttons[1]
            with patch.object(destination.QtWidgets, "QMessageBox", return_value=dialog):
                result = destination.prepare_catalogue_destination(
                    None, session, source, Path("/videos/Les glaces.json"), writer)
            self.assertEqual(result, Path("/videos/Documentaires/Les glaces.mkv"))
            self.assertEqual(session.vidb["record_id"], 123)
