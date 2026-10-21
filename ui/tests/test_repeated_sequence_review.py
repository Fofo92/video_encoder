import tempfile
import unittest
from pathlib import Path

from video_encoder_ui.repeated_sequence_review import identity, inside_occurrences, proposed_session, adjust_review_boundary


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

    def test_legacy_proposals_support_manual_out_and_in_adjustment(self):
        for index,frame,expected in [(0,74593,74593),(1,83513,83513)]:
            report=adjust_review_boundary(self.report,self.source,20243,157947,index,frame,0 if index==0 else 1)
            session=proposed_session(report,self.source,20243,157947,confirmed=True)
            self.assertEqual(session.segments[0].end_frame if index==0 else session.segments[1].start_frame,expected)
        self.assertEqual(self.report['source_motif_limits'][0]['motif_start_decoded_frame'],74597)

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


class AutomaticHypothesisTest(unittest.TestCase):
    def family(self, times):
        return {'grouping': 'each_occurrence_directly_matches_one_anchor',
                'occurrences': [{'core_start_seconds': t, 'core_end_seconds': t + 2} for t in times]}

    def test_two_families_infer_roles_from_order_without_colour_or_reference_cuts(self):
        from video_encoder_ui.repeated_sequence_review import automatic_hypothesis
        report = {'index_limits_reached': True,
                  'candidates': [self.family([25, 85, 145]), self.family([55, 115, 175])]}
        result, error = automatic_hypothesis(report, 1750, 4874)
        self.assertIsNone(error)
        self.assertEqual((result['departure'], result['resume'], result['breaks']), (1, 2, 2))
        self.assertTrue(result['search_partial'])
        self.assertTrue(result['needs_manual_review'])

    def test_one_break_can_use_outside_support(self):
        from video_encoder_ui.repeated_sequence_review import automatic_hypothesis
        report = {'candidates': [self.family([25, 85, 145]), self.family([55, 115, 175])]}
        result, error = automatic_hypothesis(report, 1750, 3374)
        self.assertIsNone(error)
        self.assertEqual(result['breaks'], 1)

    def test_absence_of_hypothesis_is_unresolved_not_zero_ad_breaks(self):
        from video_encoder_ui.repeated_sequence_review import automatic_hypothesis
        result, error = automatic_hypothesis({'candidates': []}, 0, 10000)
        self.assertIsNone(result)
        self.assertIn('ne prouve pas', error)

    def test_equal_support_does_not_silently_choose_by_group_number(self):
        from video_encoder_ui.repeated_sequence_review import automatic_hypothesis
        report = {'candidates': [self.family([100, 200, 300, 400]),
                                 self.family([110, 210, 310, 410])]}
        result, error = automatic_hypothesis(report, 0, 20000)
        self.assertIsNone(result)
        self.assertIn('même soutien', error)

    def test_more_than_two_breaks_is_not_automatically_selected(self):
        from video_encoder_ui.repeated_sequence_review import automatic_hypothesis
        result, error = automatic_hypothesis({'candidates': [self.family([100,200,300,400,500,600])]}, 0, 20000)
        self.assertIsNone(result)
        self.assertIsNotNone(error)


class ReuseExtractionSelectionTest(unittest.TestCase):
    def test_same_source_and_hypothesis_reuse_but_changed_source_or_bounds_do_not(self):
        import hashlib
        import json
        from video_encoder_ui.repeated_sequence_review import latest_extraction
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, report = root / 'source.m2t', root / 'resultat.json'
            source.write_bytes(b'source')
            report.write_text('{}')
            extracted = root / 'tmp/repeated-sequence-reviews/failed'
            extracted.mkdir(parents=True)
            (extracted / 'observation.mp4').write_bytes(b'clip')
            (extracted / 'manifest.json').write_text(json.dumps({
                'source': str(source.resolve()), 'source_identity': identity(source),
                'outer_bounds': [100, 200], 'scan_report_sha256': hashlib.sha256(report.read_bytes()).hexdigest(),
                'selected_candidate': 1, 'selected_families': None,
                'windows': [{'name': 'observation.mp4'}]}))
            choice = ['--candidate', '1']
            self.assertEqual(latest_extraction(root, source, (100, 200), report, choice), extracted)
            self.assertIsNone(latest_extraction(root, source, (101, 200), report, choice))
            self.assertIsNone(latest_extraction(root, source, (100, 200), report, ['--candidate', '2']))
            source.write_bytes(b'changed')
            self.assertIsNone(latest_extraction(root, source, (100, 200), report, choice))


class RepeatedTrajectoryTest(unittest.TestCase):
    def fragments(self, starts, count, step=2.2):
        return [{'grouping': 'each_occurrence_directly_matches_one_anchor',
                 'occurrences': [{'core_start_seconds': start + offset * step,
                                  'core_end_seconds': start + offset * step + 2}
                                 for start in starts]}
                for offset in range(count)]

    def test_many_short_groups_form_two_temporally_consistent_trajectories(self):
        from video_encoder_ui.repeated_sequence_review import repeated_trajectories
        report = {'candidates': self.fragments([100,600,1100], 13)
                               + self.fragments([200,900,1500], 7)}
        result = repeated_trajectories(report)
        self.assertEqual([len(row['member_candidates']) for row in result], [13, 7])
        self.assertEqual(len(result[0]['occurrence_spans']), 3)
        self.assertTrue(all(row['classification'] == 'unclassified_repeated_trajectory'
                            for row in result))

    def test_gaps_remain_unobserved_not_filled_as_verified_video(self):
        from video_encoder_ui.repeated_sequence_review import repeated_trajectories
        report = {'candidates': self.fragments([100,600,1100], 2, step=6)}
        result = repeated_trajectories(report)[0]
        self.assertEqual(result['occurrence_spans'][0], [100,108])
        self.assertEqual(result['observed_ranges'][0], [[100,102], [106,108]])
        self.assertEqual(result['unobserved_gap_seconds'], [4,4,4])

    def test_similar_first_occurrence_does_not_merge_inconsistent_other_occurrences(self):
        from video_encoder_ui.repeated_sequence_review import repeated_trajectories
        report = {'candidates': self.fragments([100,600,1100], 1)
                               + self.fragments([102,700,1200], 1)}
        self.assertEqual(len(repeated_trajectories(report)), 2)

    def test_no_transitive_offset_drift_between_fragment_groups(self):
        from video_encoder_ui.repeated_sequence_review import repeated_trajectories
        candidates = [self.fragments(starts, 1)[0] for starts in
                      [[100,600,1100], [102,602.3,1102.3], [104,604.6,1104.6]]]
        result = repeated_trajectories({'candidates': candidates})
        self.assertEqual([len(row['member_candidates']) for row in result], [2,1])

    def test_tied_hypotheses_explain_long_fragments_but_do_not_become_cuts(self):
        from video_encoder_ui.repeated_sequence_review import automatic_hypothesis
        report = {'candidates': self.fragments([100,600,1100], 13)
                               + self.fragments([200,900,1500], 7)}
        result, reason = automatic_hypothesis(report, 12500, 25000)
        self.assertIsNone(result)
        self.assertIn('même soutien', reason)
        self.assertIn('fragments de longues séquences', reason)

    def test_short_independent_jingles_do_not_trigger_long_fragment_diagnostic(self):
        from video_encoder_ui.repeated_sequence_review import fragmented_repeat_diagnostic
        report = {'candidates': self.fragments([100,600,1100], 1)
                               + self.fragments([200,900,1500], 1)}
        self.assertEqual(fragmented_repeat_diagnostic(report, 12500, 25000), '')
