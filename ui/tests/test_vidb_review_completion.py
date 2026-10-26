import unittest

from video_encoder_ui.vidb_review_completion import completed_record


class VidbReviewCompletionTest(unittest.TestCase):
    def test_accepts_only_the_successful_form_redirect_from_the_same_vidb_server(self):
        self.assertEqual(123, completed_record("https://vidb.test/records/123?encoder_prepared=1",
                                               "https://vidb.test/encoder_projects/episode?request_token=private"))

    def test_normal_record_pages_and_reconciliation_pages_do_not_signal_a_confirmation(self):
        for url in ("https://vidb.test/records/123", "https://vidb.test/?encoder_prepared=1",
                    "https://vidb.test/records/123?encoder_prepared=0",
                    "https://vidb.test/records/123?encoder_prepared=1&encoder_prepared=0"):
            self.assertIsNone(completed_record(url, "https://vidb.test/encoder_projects/episode"))

    def test_refuses_other_origins_credentials_and_invalid_record_ids(self):
        for url in ("https://other.test/records/123?encoder_prepared=1",
                    "http://vidb.test/records/123?encoder_prepared=1",
                    "https://vidb.test:444/records/123?encoder_prepared=1",
                    "https://user:password@vidb.test/records/123?encoder_prepared=1",
                    "https://vidb.test/records/0?encoder_prepared=1"):
            self.assertIsNone(completed_record(url, "https://vidb.test/encoder_projects/episode"))
