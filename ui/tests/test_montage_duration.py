import unittest
from fractions import Fraction
from types import SimpleNamespace
from unittest.mock import Mock, patch

from video_encoder_ui.montage_duration import (
    compare_duration, confirm_montage_duration, monitor_comparison,
)


def segment(frames, source="one", offset=0):
    return SimpleNamespace(source_id=source, start_frame=offset, end_frame=offset + frames - 1)


class MontageDurationTest(unittest.TestCase):
    def monitor(self, minutes=40, frames=60_000):
        return SimpleNamespace(
            trim_project_writer=SimpleNamespace(vidb_result={"status": "identified", "metadata": {
                "reference_runtime_minutes": minutes}}),
            trim_session=SimpleNamespace(segments=[segment(frames)]),
            frame_source=SimpleNamespace(frame_rate_numerator=25, frame_rate_denominator=1))

    def test_same_duration_needs_no_warning(self):
        comparison = monitor_comparison(self.monitor())
        self.assertEqual(Fraction(2400), comparison.montage_seconds)
        self.assertFalse(comparison.needs_warning)

    def test_forty_minutes_allow_exactly_thirty_six_through_forty_four_minutes(self):
        for frames, warning in ((54_000, False), (66_000, False), (53_999, True), (66_001, True)):
            with self.subTest(frames=frames):
                self.assertEqual(warning, monitor_comparison(self.monitor(frames=frames)).needs_warning)

    def test_short_program_uses_the_three_minute_minimum(self):
        self.assertFalse(compare_duration(10, [segment(7 * 60 * 25)], 25).needs_warning)
        self.assertTrue(compare_duration(10, [segment(7 * 60 * 25 - 1)], 25).needs_warning)

    def test_multisource_adds_only_kept_segments_not_whole_sources(self):
        parts = [segment(10 * 60 * 25, "one", 100_000), segment(30 * 60 * 25, "two", 20_000)]
        comparison = compare_duration(40, parts, 25)
        self.assertEqual(Fraction(2400), comparison.montage_seconds)
        self.assertFalse(comparison.needs_warning)

    def test_fractional_frame_rate_is_not_rounded(self):
        monitor = self.monitor(frames=72_000)
        monitor.frame_source = SimpleNamespace(frame_rate_numerator=30_000, frame_rate_denominator=1001)
        monitor.frames_per_second = 30
        self.assertEqual(Fraction(12012, 5), monitor_comparison(monitor).montage_seconds)

    def test_invalid_or_missing_reference_skips_comparison(self):
        for value in (None, 0, -1, True, "nan", "inf", "", "unknown"):
            with self.subTest(value=value):
                self.assertIsNone(monitor_comparison(self.monitor(minutes=value)))
                self.assertTrue(confirm_montage_duration(self.monitor(minutes=value)))

    def test_unidentified_project_does_not_use_previous_metadata(self):
        monitor = self.monitor()
        monitor.trim_project_writer.vidb_result["status"] = "unmatched"
        self.assertIsNone(monitor_comparison(monitor))
        self.assertTrue(confirm_montage_duration(monitor))

    def test_empty_montage_and_invalid_frame_data_skip_comparison(self):
        self.assertIsNone(compare_duration(40, [], 25))
        self.assertIsNone(compare_duration(40, [segment(100)], 0))
        self.assertIsNone(compare_duration(40, [SimpleNamespace(start_frame=5, end_frame=1)], 25))
        self.assertIsNone(compare_duration(40, [SimpleNamespace(start_frame=-1, end_frame=5)], 25))

    def test_compatible_duration_does_not_open_any_dialog(self):
        self.assertTrue(confirm_montage_duration(self.monitor()))
        self.assertTrue(confirm_montage_duration(SimpleNamespace()))

    def test_reference_survives_save_but_not_a_different_binding(self):
        monitor = self.monitor(frames=20 * 60 * 25)
        result = monitor.trim_project_writer.vidb_result
        result.update(project_id="project-one", record_id=123)
        self.assertTrue(monitor_comparison(monitor).needs_warning)
        result.pop("metadata")
        self.assertTrue(monitor_comparison(monitor).needs_warning)
        result["record_id"] = 456
        self.assertIsNone(monitor_comparison(monitor))
        result["record_id"] = 123
        result["project_id"] = "project-two"
        self.assertIsNone(monitor_comparison(monitor))

    def test_old_project_reference_does_not_apply_to_new_montage(self):
        monitor = self.monitor(frames=20 * 60 * 25)
        monitor.trim_session.project_id = "new-project"
        monitor.trim_project_writer.vidb_result["project_id"] = "previous-project"
        self.assertIsNone(monitor_comparison(monitor))

    def decision(self, selected):
        monitor = self.monitor(frames=27 * 60 * 25)
        back, proceed = object(), object()
        dialog = Mock()
        dialog.addButton.side_effect = [back, proceed]
        dialog.clickedButton.return_value = {"back": back, "continue": proceed, "closed": None}[selected]
        qt = Mock()
        qt.QMessageBox.return_value = dialog
        with patch.dict("sys.modules", {"PySide6": SimpleNamespace(QtWidgets=qt)}):
            result = confirm_montage_duration(monitor)
        dialog.setDefaultButton.assert_called_once_with(back)
        text = dialog.setText.call_args.args[0]
        self.assertIn("40 min", text)
        self.assertIn("27 min", text)
        return result

    def test_return_to_montage_cancels_saving(self):
        self.assertFalse(self.decision("back"))

    def test_closing_warning_cancels_saving(self):
        self.assertFalse(self.decision("closed"))

    def test_explicit_continue_allows_saving(self):
        self.assertTrue(self.decision("continue"))

    def test_changes_are_recalculated_for_each_save(self):
        monitor = self.monitor()
        self.assertFalse(monitor_comparison(monitor).needs_warning)
        monitor.trim_session.segments = [segment(20 * 60 * 25)]
        self.assertTrue(monitor_comparison(monitor).needs_warning)


if __name__ == "__main__":
    unittest.main()
