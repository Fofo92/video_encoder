"""Compare catalogue runtime with the kept timeline, without inspecting media again."""
from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class DurationComparison:
    expected_seconds: Fraction
    montage_seconds: Fraction
    tolerance_seconds: Fraction

    @property
    def needs_warning(self):
        return abs(self.montage_seconds - self.expected_seconds) > self.tolerance_seconds


def positive_number(value):
    if isinstance(value, bool):
        return None
    try:
        number = Fraction(str(value))
    except (ValueError, TypeError, ZeroDivisionError):
        return None
    return number if number > 0 else None


def compare_duration(expected_minutes, segments, frame_rate):
    expected = positive_number(expected_minutes)
    cadence = positive_number(frame_rate)
    if expected is None or cadence is None or not segments:
        return None
    frames = 0
    for segment in segments:
        start, end = getattr(segment, "start_frame", None), getattr(segment, "end_frame", None)
        if type(start) is not int or type(end) is not int or start < 0 or end < start:
            return None
        frames += end - start + 1  # IN and OUT are inclusive, as in the exporter.
    seconds = expected * 60
    return DurationComparison(seconds, Fraction(frames) / cadence, max(Fraction(180), seconds / 10))


def format_duration(seconds):
    total = int(seconds + Fraction(1, 2))
    minutes, remainder = divmod(total, 60)
    return f"{minutes} min {remainder:02d} s" if remainder else f"{minutes} min"


def runtime_reference(monitor, result):
    key = (result.get("project_id"), result.get("record_id"))
    metadata = result.get("metadata")
    if isinstance(metadata, dict):
        minutes = metadata.get("reference_runtime_minutes")
        monitor._runtime_reference = ((key, minutes) if all(key) and positive_number(minutes) is not None else None)
        return minutes
    # The project JSON deliberately omits metadata. Keep this reference only in
    # memory across saves of the same binding, never across projects or records.
    previous = getattr(monitor, "_runtime_reference", None)
    return previous[1] if all(key) and previous is not None and previous[0] == key else None


def monitor_comparison(monitor):
    writer = getattr(monitor, "trim_project_writer", None)
    result = getattr(writer, "vidb_result", None)
    if not isinstance(result, dict) or result.get("status") != "identified":
        return None
    session = getattr(monitor, "trim_session", None)
    project_id = getattr(session, "project_id", None)
    if project_id is not None and project_id != result.get("project_id"):
        return None
    preview = getattr(monitor, "frame_source", None)
    numerator = getattr(preview, "frame_rate_numerator", None)
    denominator = getattr(preview, "frame_rate_denominator", None)
    if type(numerator) is int and type(denominator) is int and numerator > 0 and denominator > 0:
        cadence = Fraction(numerator, denominator)
    else:
        cadence = getattr(monitor, "frames_per_second", None)
    return compare_duration(runtime_reference(monitor, result), getattr(session, "segments", ()), cadence)


def confirm_montage_duration(monitor):
    comparison = monitor_comparison(monitor)
    if comparison is None or not comparison.needs_warning:
        return True

    from PySide6 import QtWidgets

    dialog = QtWidgets.QMessageBox(monitor)
    dialog.setWindowTitle("Durée du montage à vérifier")
    dialog.setIcon(QtWidgets.QMessageBox.Icon.Warning)
    dialog.setText(f"Durée attendue : {format_duration(comparison.expected_seconds)}\n"
                   f"Durée du montage : {format_duration(comparison.montage_seconds)}")
    dialog.setInformativeText("Un segment manque peut-être ou l’œuvre identifiée ne correspond pas.\n"
                              "La durée du catalogue reste indicative. Aucun projet n’a encore été enregistré.")
    back = dialog.addButton("Revenir au montage", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    proceed = dialog.addButton("Continuer malgré l’écart", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    from .proposal_revision import can_review_proposal, review_proposal

    review = None
    if can_review_proposal(monitor):
        review = dialog.addButton("Revoir la proposition vidb…", QtWidgets.QMessageBox.ButtonRole.ActionRole)
    dialog.setDefaultButton(back)
    dialog.exec()
    if review is not None and dialog.clickedButton() is review:
        review_proposal(monitor)
        # The identity/runtime/destination may have changed. Never write the old
        # destination or enqueue a job from this interrupted save attempt.
        if hasattr(monitor, "statusBar"):
            monitor.statusBar().showMessage(
                "Proposition réexaminée. Relance la préparation pour vérifier la destination et la durée.", 10000)
        return False
    return dialog.clickedButton() is proceed

