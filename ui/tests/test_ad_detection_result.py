import json
import os
import tempfile
import unittest
from pathlib import Path

from video_encoder_ui.ad_detection_result import empty_detection_report


class EmptyDetectionResultTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "Braveheart.m2t"
        self.source.write_bytes(b"source")
        (self.root / "detection").mkdir()
        self.report = self.root / "detection" / "pub-candidates.json"
        self.document = {
            "format": "video_encoder.6ter_pub_candidates", "version": 3,
            "source": str(self.source), "complete": True, "ffmpeg_exit_status": 0,
            "candidate_count": 0, "candidates": [], "analysed_samples": 24000,
            "requested_start_seconds": None, "requested_duration_seconds": None,
        }

    def write(self, changes=None):
        self.report.write_text(json.dumps(self.document | (changes or {})))

    def test_recognizes_the_completed_zero_candidate_scan_without_a_boundary_report(self):
        self.write()
        self.assertEqual(empty_detection_report(self.root, self.source), self.report)

    def test_refuses_incomplete_failed_partial_or_different_source_results(self):
        for changes in [
            {"complete": False}, {"ffmpeg_exit_status": 1}, {"analysed_samples": 0},
            {"requested_start_seconds": 10}, {"requested_duration_seconds": 120},
            {"source": str(self.root / "other.m2t")}, {"candidate_count": 2}, {"candidates": [{}]},
        ]:
            with self.subTest(changes=changes):
                self.write(changes)
                self.assertIsNone(empty_detection_report(self.root, self.source))

    def test_a_source_modified_after_detection_requires_a_new_result(self):
        self.write()
        newer = self.report.stat().st_mtime_ns + 1000000000
        os.utime(self.source, ns=(newer, newer))
        self.assertIsNone(empty_detection_report(self.root, self.source))

    def test_missing_or_malformed_report_is_not_an_empty_success(self):
        self.assertIsNone(empty_detection_report(self.root, self.source))
        for text in ["{", "[]", "null"]:
            self.report.write_text(text)
            self.assertIsNone(empty_detection_report(self.root, self.source))
