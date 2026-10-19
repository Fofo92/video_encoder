import tempfile
import unittest
from pathlib import Path

from video_encoder_ui.repeated_sequence_review import identity, inside_occurrences, proposed_session


class RepeatedSequenceReviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.m2t'
        self.source.write_bytes(b'source')
        self.report = {'status': 'experimental', 'source': str(self.source),
                       'source_identity': identity(self.source), 'outer_bounds': [20243, 157947],
                       'coordinate_basis': 'FFmpeg decoded source frame index; editor mapping unverified',
                       'refinement': {'status': 'experimental'},
                       'source_motif_limits': [
                           {'motif_start_decoded_frame': start, 'motif_end_decoded_frame_exclusive': end}
                           for start, end in [(74597, 74672), (83441, 83516), (120823, 120898), (130151, 130226)]]}

    def test_confirmed_departure_resume_pairs_produce_three_segments_with_inclusive_out(self):
        session = proposed_session(self.report, self.source, 20243, 157947, confirmed=True)
        self.assertEqual([(row.start_frame, row.end_frame) for row in session.segments],
                         [(20243, 74596), (83516, 120822), (130226, 157947)])
        self.assertEqual(self.source.read_bytes(), b'source')

    def test_no_segments_without_explicit_semantic_confirmation(self):
        with self.assertRaises(ValueError):
            proposed_session(self.report, self.source, 20243, 157947)

    def test_rejects_odd_or_overlapping_occurrences(self):
        self.report['source_motif_limits'].pop()
        with self.assertRaises(ValueError):
            proposed_session(self.report, self.source, 20243, 157947, confirmed=True)
        self.report['source_motif_limits'].append(self.report['source_motif_limits'][0])
        with self.assertRaises(ValueError):
            proposed_session(self.report, self.source, 20243, 157947, confirmed=True)

    def test_rejects_changed_source_and_resampled_coordinates(self):
        self.report['coordinate_basis'] = 'resampled'
        with self.assertRaises(ValueError):
            proposed_session(self.report, self.source, 20243, 157947, confirmed=True)
        self.source.write_bytes(b'changed')
        with self.assertRaises(ValueError):
            proposed_session(self.report, self.source, 20243, 157947, confirmed=True)

    def test_outer_bounds_filter_does_not_classify_the_occurrences(self):
        candidate = {'occurrences': [{'core_start_seconds': 1, 'core_end_seconds': 3},
                                     {'core_start_seconds': 100, 'core_end_seconds': 103}]}
        self.assertEqual(inside_occurrences(candidate, 2000, 3000), candidate['occurrences'][1:])

    def test_reopens_latest_discovery_for_the_same_unchanged_source(self):
        import json
        from video_encoder_ui.repeated_sequence_review import latest_discovery
        repository = Path(self.temp.name)
        folder = repository / 'tmp' / 'previous'
        folder.mkdir(parents=True)
        report = {**self.report, 'sample_fps': 5, 'candidates': []}
        path = folder / 'resultat.json'
        path.write_text(json.dumps(report))
        self.assertEqual(latest_discovery(repository, self.source), path)
        self.source.write_bytes(b'changed')
        self.assertIsNone(latest_discovery(repository, self.source))
