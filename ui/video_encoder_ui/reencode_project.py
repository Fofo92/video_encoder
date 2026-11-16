"""Create a fresh export document from an open montage, without overwriting it."""
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path

from .media_inspection_client import MediaInspectionError
from .original_language_review import selection_scope
from .track_options import choose_track_mode, preferred_mode, track_capabilities
from .trim_project_file_writer import TrimProjectFileWriter
from .trim_session import SourceReference, TrimSession
from .vidb_project_link import VidbProjectLink


@dataclass
class ReencodePreparation:
    session: TrimSession
    project_path: Path
    output_path: Path


def project_document(session):
    return {"version": 2, "project_id": getattr(session, "project_id", None),
            "vidb": getattr(session, "vidb", {}),
            "sources": [TrimSession.serialize_source(source) for source in session.sources],
            "timeline": [{"type": "segment", "source_id": segment.source_id,
                          "start_frame": segment.start_frame, "end_frame": segment.end_frame}
                         for segment in session.segments]}


def clone_session(session, capabilities, mode):
    clone = TrimSession()
    for source in session.sources:
        inspection = capabilities["inspections"].get(str(source.path), source.inspection)
        clone.add_source(SourceReference(source.identifier, source.path, deepcopy(inspection)))
    for segment in session.segments:
        clone.add_segment(segment)
    clone.project_id = VidbProjectLink.project_id(session)
    clone.vidb = deepcopy(getattr(session, "vidb", {}))
    clone.vidb_launch = getattr(session, "vidb_launch", None)
    if getattr(session, "copy_condition", None) is not None:
        clone.copy_condition = deepcopy(session.copy_condition)
    clone.track_selection = {"mode": mode, "scope": selection_scope(project_document(clone)),
                             "confirmed_by": "user", "evidence": {"policy": "explicit_reencode_track_review"}}
    return clone


def suggested_output(path, mode):
    labels = {"french_only": "VF", "original_without_subtitles": "VM", "original_with_subtitles": "VMST"}
    project = Path(path)
    stem = f"{project.stem} - réencodage {labels[mode]}"
    candidate = project.with_name(stem + ".mkv")
    index = 2
    while (candidate.exists() or candidate.is_symlink()
           or candidate.with_suffix(".json").exists() or candidate.with_suffix(".json").is_symlink()):
        candidate = project.with_name(f"{stem} {index}.mkv")
        index += 1
    return candidate


def report_error(parent, message):
    from PySide6 import QtWidgets
    QtWidgets.QMessageBox.warning(parent, "Réencodage non préparé", message)


def prepare_reencode(monitor, *, choose=None, select_output=None, report=None):
    original = getattr(monitor, "project_path", None)
    writer = monitor.trim_project_writer
    previous_result = deepcopy(getattr(writer, "vidb_result", {}))
    try:
        if original is None or not Path(original).is_file():
            raise ValueError("Ouvre un projet JSON enregistré avant de préparer son réencodage.")
        session = monitor.trim_session
        if not session.segments:
            raise ValueError("Le montage ne contient aucun segment.")
        capabilities = track_capabilities(project_document(session), monitor.media_inspection_client)
        if not capabilities or preferred_mode(capabilities) is None:
            raise ValueError("Les sources utilisées ne permettent aucune des versions VF, VM ou VMST.")
        current = (getattr(session, "track_selection", None) or {}).get("mode")
        mode = (choose or choose_track_mode)(monitor, capabilities, current)
        if mode is None:
            return None
        if not capabilities.get(mode) or mode not in {"french_only", "original_without_subtitles", "original_with_subtitles"}:
            raise ValueError("Les pistes de cette version ne sont pas présentes sur toutes les sources utilisées.")
        if select_output is None:
            from .project_destination import select_project_output
            select_output = select_project_output
        output = select_output(monitor, suggested_output(original, mode))
        if output is None:
            return None
        output = Path(output)
        if output.suffix.lower() != ".mkv" or output.exists() or output.is_symlink():
            raise ValueError("Choisis une nouvelle destination MKV pour conserver l’ancien encodage.")
        clone = clone_session(session, capabilities, mode)
        selection = deepcopy(clone.track_selection)
        destination = output.with_suffix(".json")
        writer.save(clone, destination, exclusive=True)
        document = json.loads(destination.read_text(encoding="utf-8"))
        before_record = (getattr(session, "vidb", {}) or {}).get("record_id")
        after_record = (document.get("vidb") or {}).get("record_id")
        if before_record is not None and before_record != after_record:
            raise ValueError("L’association vidb a changé. Vérifie le nouveau projet avant de lancer son encodage.")
        selection["scope"] = selection_scope(document)
        clone.track_selection = selection
        document["track_selection"] = selection
        TrimProjectFileWriter.write_atomic(destination, json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        return ReencodePreparation(clone, destination, output)
    except (OSError, ValueError, TypeError, KeyError, MediaInspectionError) as error:
        writer.vidb_result = previous_result
        (report or report_error)(monitor, str(error))
        return None
