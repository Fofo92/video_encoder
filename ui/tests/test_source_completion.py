import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

try:
    from PySide6 import QtWidgets
except ModuleNotFoundError as error:
    if error.name != "PySide6":
        raise
    raise unittest.SkipTest("PySide6 is unavailable") from error

from video_encoder_ui.source_completion_controller import SourceCompletionController
from video_encoder_ui.source_completion_plan import SourceCompletionPlan, SourceCompletionError
from video_encoder_ui.source_quarantine_client import SourceQuarantineError


class SourceCompletionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "deux programmes.m2t"
        self.source.write_bytes(b"capture")
        self.plan = SourceCompletionPlan(self.root)
        self.first = self.job("premier")
        self.queue = Mock()
        self.queue.list_jobs.return_value = [self.first]
        self.quarantine = Mock()
        self.controller = SourceCompletionController(None, self.queue, self.quarantine, self.plan)
        self.addCleanup(self.close_controller)

    def close_controller(self):
        self.controller.timer.stop()
        if self.controller.dialog is not None:
            self.controller.dialog.blockSignals(True)
            self.controller.dialog.close()
            self.controller.dialog.deleteLater()
        self.controller.deleteLater()

    def job(self, name, status="done", source=None, version=2):
        project = self.root / f"{name}.json"
        paths = [str(source or self.source)]
        document = {"format": "video_encoder.trim_project", "version": version}
        if version == 2:
            document["sources"] = [{"id": "source", "path": path} for path in paths]
        else:
            document["timeline"] = [{"type": "segment", "source": path} for path in paths]
        project.write_text(json.dumps(document), encoding="utf-8")
        output = self.root / f"{name}.mkv"
        if status == "done":
            output.write_bytes(b"encoded")
        return {"id": name, "kind": "trim_export", "status": status,
                "input_path": str(project), "output_path": str(output), "finished_at": name}

    def test_unknown_future_program_never_causes_automatic_quarantine(self):
        self.controller.poll()
        self.assertIsNotNone(self.controller.dialog)
        self.assertFalse(self.controller.dialog.isModal())
        self.quarantine.quarantine.assert_not_called()
        keep = next(button for button in self.controller.dialog.findChildren(QtWidgets.QPushButton)
                    if button.text().startswith("Il reste"))
        self.assertTrue(keep.isDefault())
        keep.click()
        self.assertTrue(self.source.exists())
        self.quarantine.quarantine.assert_not_called()

    def test_closing_the_question_also_preserves_the_source(self):
        self.controller.poll()
        self.controller.dialog.close()
        self.quarantine.quarantine.assert_not_called()
        self.assertTrue(self.source.exists())

    def test_second_unprepared_program_can_be_encoded_before_confirming_the_source(self):
        self.controller.poll()
        self.controller.dialog.reject()
        second = self.job("second", "queued")
        self.queue.list_jobs.return_value = [self.first, second]
        self.controller.poll()
        self.assertIsNone(self.controller.dialog)
        second = self.job("second", "done")
        self.queue.list_jobs.return_value = [self.first, second]
        self.controller.poll()
        self.assertIsNotNone(self.controller.dialog)
        self.assertEqual(2, len(self.controller.case.outputs))
        self.controller.confirm()
        self.quarantine.quarantine.assert_called_once_with(self.source)

    def test_every_known_unfinished_job_protects_its_source(self):
        for status in ("queued", "running", "deferred", "failed", "interrupted"):
            with self.subTest(status=status):
                other = self.job("second", status)
                self.assertEqual([], self.plan.collect([self.first, other]))

    def test_source_with_a_missing_encoded_output_is_preserved(self):
        Path(self.first["output_path"]).unlink()
        self.assertEqual([], self.plan.collect([self.first]))

    def test_a_symbolic_output_is_not_a_verified_encoded_file(self):
        output = Path(self.first["output_path"])
        output.unlink()
        output.symlink_to(self.source)
        self.assertEqual([], self.plan.collect([self.first]))

    def test_files_outside_the_capture_directory_are_never_proposed(self):
        other = self.root / "autre"
        other.mkdir()
        plan = SourceCompletionPlan(other)
        self.assertEqual([], plan.collect([self.first]))

    def test_a_malformed_pending_project_preserves_sources(self):
        second = self.job("second", "queued")
        Path(second["input_path"]).write_text('[]', encoding="utf-8")
        with self.assertRaises(SourceCompletionError):
            self.plan.collect([self.first, second])

    def test_unreadable_pending_project_protects_sources(self):
        second = self.job("second", "queued")
        Path(second["input_path"]).unlink()
        with self.assertRaises(SourceCompletionError):
            self.plan.collect([self.first, second])

    def test_changes_while_the_question_is_open_require_another_review(self):
        self.controller.poll()
        self.queue.list_jobs.return_value = [self.first, self.job("second", "queued")]
        with patch.object(QtWidgets.QMessageBox, "warning"):
            self.controller.confirm()
        self.quarantine.quarantine.assert_not_called()
        self.assertTrue(self.source.exists())

    def test_replaced_output_is_not_accepted_after_the_confirmation_was_displayed(self):
        case = self.plan.collect([self.first])[0]
        Path(self.first["output_path"]).write_bytes(b"replacement")
        with self.assertRaises(SourceCompletionError):
            self.plan.validate(case, [self.first])

    def test_changed_source_is_not_quarantined(self):
        case = self.plan.collect([self.first])[0]
        self.source.write_bytes(b"replacement capture")
        with self.assertRaises(SourceCompletionError):
            self.plan.validate(case, [self.first])

    def test_unchanged_source_supports_both_project_versions(self):
        for version in (1, 2):
            with self.subTest(version=version):
                job = self.job("version", version=version)
                case = self.plan.collect([job])[0]
                self.assertEqual(self.source, self.plan.validate(case, [job]).source)

    def test_existing_completed_history_is_not_prompted_on_startup(self):
        self.controller.start()
        self.controller.poll()
        self.assertIsNone(self.controller.dialog)

    def test_manual_review_can_reopen_a_declined_source(self):
        self.controller.poll()
        self.controller.dialog.reject()
        self.controller.poll()
        self.assertIsNone(self.controller.dialog)
        self.controller.poll(inspect_all=True)
        self.assertIsNotNone(self.controller.dialog)

    def test_successful_direct_export_is_also_reviewed(self):
        self.queue.list_jobs.return_value = []
        self.controller.record_export(self.first["input_path"], self.first["output_path"])
        self.controller.poll()
        self.assertIsNotNone(self.controller.dialog)
        self.quarantine.quarantine.assert_not_called()

    def multisource_job(self, version=2):
        second = self.root / "autre capture.m2t"
        second.write_bytes(b"second capture")
        job = self.job("multisource", version=version)
        project = Path(job["input_path"])
        document = json.loads(project.read_text(encoding="utf-8"))
        if version == 2:
            document["sources"].append({"id": "second", "path": str(second)})
        else:
            document["timeline"].append({"type": "segment", "source": str(second)})
        project.write_text(json.dumps(document), encoding="utf-8")
        self.queue.list_jobs.return_value = [job]
        return job, second

    def test_confirming_first_source_still_proposes_second_source_of_same_job(self):
        _job, second = self.multisource_job()
        self.quarantine.quarantine.side_effect = lambda source: source.unlink()
        self.controller.poll()
        self.assertEqual(self.source, self.controller.case.source)
        self.controller.confirm()
        self.assertFalse(self.source.exists())
        self.controller.poll()
        self.assertIsNotNone(self.controller.dialog)
        self.assertEqual(second, self.controller.case.source)
        self.controller.confirm()
        self.controller.poll()
        self.assertIsNone(self.controller.dialog)
        self.assertEqual([self.source, second],
                         [call.args[0] for call in self.quarantine.quarantine.call_args_list])

    def test_declining_first_source_does_not_decline_second_even_for_version_one(self):
        _job, second = self.multisource_job(version=1)
        self.controller.poll()
        self.controller.dialog.reject()
        self.controller.poll()
        self.assertIsNotNone(self.controller.dialog)
        self.assertEqual(second, self.controller.case.source)
        self.controller.confirm()
        self.controller.poll()
        self.assertIsNone(self.controller.dialog)
        self.quarantine.quarantine.assert_called_once_with(second)
        self.assertTrue(self.source.exists())

    def test_blocked_second_source_is_proposed_when_its_unfinished_job_is_removed(self):
        job, second = self.multisource_job()
        unfinished = self.job("still queued", status="queued", source=second)
        self.queue.list_jobs.return_value = [job, unfinished]
        self.controller.poll()
        self.assertEqual(self.source, self.controller.case.source)
        self.controller.confirm()
        self.controller.poll()
        self.assertIsNone(self.controller.dialog)
        self.quarantine.quarantine.assert_called_once_with(self.source)
        self.queue.list_jobs.return_value = [job]
        self.controller.poll()
        self.assertEqual(second, self.controller.case.source)
        self.controller.confirm()
        self.assertEqual(2, self.quarantine.quarantine.call_count)

    def test_new_completion_can_ask_again_about_a_previously_declined_source(self):
        self.controller.poll()
        self.controller.dialog.reject()
        self.controller.poll()
        self.assertIsNone(self.controller.dialog)
        self.queue.list_jobs.return_value = [self.first, self.job("new export")]
        self.controller.poll()
        self.assertIsNotNone(self.controller.dialog)
        self.assertEqual(self.source, self.controller.case.source)

    def test_backend_refusal_keeps_the_question_and_source(self):
        self.controller.poll()
        self.quarantine.quarantine.side_effect = SourceQuarantineError("source encore utilisée")
        with patch.object(QtWidgets.QMessageBox, "warning"):
            self.controller.confirm()
        self.assertIsNotNone(self.controller.dialog)
        self.assertTrue(self.source.exists())
