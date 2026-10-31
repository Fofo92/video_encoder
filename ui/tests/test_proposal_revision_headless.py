import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch


class ProposalRevisionHeadlessTest(unittest.TestCase):
    def test_availability_check_does_not_import_the_graphical_browser(self):
        path = Path(__file__).resolve().parents[1] / 'video_encoder_ui/proposal_revision.py'
        spec = importlib.util.spec_from_file_location('video_encoder_ui._headless_revision_check', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict('sys.modules', {'video_encoder_ui.vidb_montage_review': None}):
            spec.loader.exec_module(module)
            self.assertFalse(module.can_review_proposal(SimpleNamespace()))
            monitor = SimpleNamespace(trim_project_writer=SimpleNamespace(vidb_result={'selection_url': '/select'}))
            self.assertTrue(module.can_review_proposal(monitor))

    def test_explicit_review_forwards_arguments_to_the_graphical_controller(self):
        path = Path(__file__).resolve().parents[1] / 'video_encoder_ui/proposal_revision.py'
        spec = importlib.util.spec_from_file_location('video_encoder_ui._lazy_revision_check', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        calls = []
        browser = SimpleNamespace(review_montage_identification=lambda *args, **kwargs: calls.append((args, kwargs)))
        with patch.dict('sys.modules', {'video_encoder_ui.vidb_montage_review': browser}):
            module.review_montage_identification('monitor', session='session')
        self.assertEqual([(('monitor',), {'session': 'session'})], calls)
