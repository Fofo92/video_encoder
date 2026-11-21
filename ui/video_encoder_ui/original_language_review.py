"""Choose tracks before audio analysis and subtitle extraction/OCR."""
import json
from pathlib import Path


def selection_scope(document):
    vidb = document.get("vidb") or {}
    if document.get("version") == 1:
        paths = [item["source"] for item in document.get("timeline", []) if "source" in item]
    else:
        paths = [source["path"] for source in document.get("sources", [])]
    return {"project_id": document.get("project_id"), "record_id": vidb.get("record_id"),
            "source_paths": sorted(set(paths))}


def proposed_mode(result):
    if not isinstance(result, dict) or result.get("status") != "identified":
        return None
    metadata = result.get("metadata") or {}
    version = metadata.get("language_version")
    evidence = metadata.get("original_language_evidence") or {}
    modes = {"VF": "french_only", "VM": "original_without_subtitles", "VMST": "original_with_subtitles"}
    # A catalogue VF with unknown original language is not a confirmed project track choice.
    uncertain_vf = (version == "VF" and metadata.get("language_version_explicit") is not True
                    and evidence.get("status") in (None, "unknown"))
    if version in modes and not uncertain_vf:
        return modes[version]
    if evidence.get("provider") != "tmdb":
        return None
    language = evidence.get("language")
    if evidence.get("status") == "french" and language == "fr":
        return "french_only"
    if (evidence.get("status") == "foreign" and isinstance(language, str)
            and len(language) == 2 and language.isascii() and language.islower() and language != "fr"):
        return "original_with_subtitles"
    return None


def ask_mode(parent):
    from PySide6 import QtWidgets

    box = QtWidgets.QMessageBox(parent)
    box.setWindowTitle("Langue originale à confirmer")
    box.setIcon(QtWidgets.QMessageBox.Icon.Question)
    box.setText("La fiche externe ne permet pas d’établir la langue originale avec certitude.\n\n"
                "La version originale de cette œuvre est-elle en français ?\n\n"
                "Français : une piste audio française, sans sous-titres complets.\n"
                "Les sous-titres explicitement marqués forcés restent conservés.\n"
                "Autre langue : parcours habituel avec VO et sous-titres français.\n"
                "Ce choix s’applique à toutes les sources de ce montage.")
    back = box.addButton("Revenir au montage", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    french = box.addButton("Oui, VO française", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    foreign = box.addButton("Non, VO étrangère", QtWidgets.QMessageBox.ButtonRole.ActionRole)
    box.setDefaultButton(back)
    box.setEscapeButton(back)
    box.exec()
    if box.clickedButton() == french:
        return "french_only"
    if box.clickedButton() == foreign:
        return "original_with_subtitles"
    return None


def bound_mode(result, scope):
    if result.get("project_id") != scope["project_id"] or result.get("record_id") != scope["record_id"]:
        return None
    return proposed_mode(result)


def prepare_track_selection(monitor, project_path, choose=None):
    from .trim_project_file_writer import TrimProjectFileWriter
    from .track_options import track_capabilities
    from .media_inspection_client import MediaInspectionError

    path = Path(project_path)
    writer = monitor.trim_project_writer
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        scope = selection_scope(document)
        previous = document.get("track_selection")
        link = getattr(writer, "vidb_link", None)
        result = getattr(writer, "vidb_result", {})
        mode = None
        if (isinstance(previous, dict) and previous.get("scope") == scope
                and previous.get("mode") in {"french_only", "original_with_subtitles", "original_without_subtitles"}):
            if link is not None and previous.get("confirmed_by") in {"external", "source_default"}:
                result = link.identify(document, path, refresh=True)
                writer.vidb_result = result
                mode = bound_mode(result, scope)
            if mode is None or mode == previous["mode"]:
                monitor.trim_session.track_selection = previous
                return True
        else:
            mode = bound_mode(result, scope)
            if mode is None and link is not None:
                # Restored projects deliberately omit vidb metadata; request it again.
                result = link.identify(document, path, refresh=True)
                writer.vidb_result = result
                mode = bound_mode(result, scope)
        origin = "external" if mode is not None else None
        if mode is None:
            capabilities = track_capabilities(document, getattr(monitor, "media_inspection_client", None))
            if capabilities and capabilities["original_with_subtitles"]:
                mode = "original_with_subtitles"
                origin = "source_default"
        if mode is None:
            mode = (choose or ask_mode)(monitor)
        if mode is None:
            return False
        selection = {"mode": mode, "scope": scope, "confirmed_by": origin or "user"}
        if origin == "external":
            selection["evidence"] = {"language_version": result["metadata"].get("language_version"),
                                     "original_language_evidence": result["metadata"].get("original_language_evidence")}
        elif origin == "source_default":
            selection["evidence"] = {"policy": "prefer_vmst_when_uncertain",
                                     "inspected_sources": list(capabilities["inspections"])}
        document["track_selection"] = selection
        TrimProjectFileWriter.write_atomic(path, json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        monitor.trim_session.track_selection = selection
        label = "Audio français seul, sous-titres forcés uniquement" if mode == "french_only" else ("Audio français et VO, sans sous-titres complets"
                if mode == "original_without_subtitles" else "VO et sous-titres français")
        monitor.statusBar().showMessage(label, 8_000)
        return True
    except (OSError, ValueError, TypeError, KeyError, MediaInspectionError) as error:
        from PySide6 import QtWidgets
        QtWidgets.QMessageBox.warning(monitor, "Sélection des pistes impossible", str(error))
        return False
