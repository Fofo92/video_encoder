import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from video_encoder_ui import vidb_project_review as review
except ModuleNotFoundError:
    review = None


@unittest.skipIf(review is None, "PySide6 is unavailable")
class VidbProjectReviewTest(unittest.TestCase):
    def test_identified_or_unconfigured_projects_continue_without_a_dialog(self):
        with patch.object(review.QtWidgets, "QMessageBox") as dialog:
            self.assertTrue(review.offer_vidb_review(None, None, True))
            for status in ("identified", "disabled"):
                self.assertTrue(review.offer_vidb_review(None, SimpleNamespace(vidb_result={"status": status}), True))
            dialog.assert_not_called()

    def test_opening_vidb_pauses_this_export_and_opens_only_its_review_page(self):
        writer = SimpleNamespace(vidb_result={"status": "needs_review", "review_url": "https://vidb.test/review"})
        with patch.object(review.QtWidgets, "QMessageBox") as box, patch.object(review, "open_vidb_modal") as opened:
            first, second, third = Mock(), Mock(), Mock()
            box.return_value.addButton.side_effect = [first, second, third]
            box.return_value.clickedButton.return_value = first
            self.assertFalse(review.offer_vidb_review(None, writer, True))
            self.assertEqual(opened.call_args.args[1], "https://vidb.test/review")

    def test_the_user_can_encode_while_vidb_is_unavailable(self):
        writer = SimpleNamespace(vidb_result={"status": "pending"})
        with patch.object(review.QtWidgets, "QMessageBox") as box:
            proceed, back = Mock(), Mock()
            box.return_value.addButton.side_effect = [proceed, back]
            box.return_value.clickedButton.return_value = proceed
            self.assertTrue(review.offer_vidb_review(None, writer, True))
