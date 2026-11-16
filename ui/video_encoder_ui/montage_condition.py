"""Declared condition of the retained montage, independent of its language tracks."""
from copy import deepcopy
from datetime import datetime, timezone


def source_paths(session):
    used = {segment.source_id for segment in session.segments}
    return sorted({str(source.path) for source in session.sources if source.identifier in used})


def checked_condition(value):
    if not isinstance(value, dict):
        raise ValueError("État du montage invalide.")
    allowed = {"integrality", "damage", "retained_portion", "note", "declared_at",
               "source_paths", "affected_source_paths"}
    if set(value) != allowed:
        raise ValueError("Déclaration d’état du montage incomplète ou non reconnue.")
    if (value["integrality"] not in ("complete", "incomplete")
            or value["damage"] not in ("none", "light", "severe")
            or value["retained_portion"] not in ("unknown", "beginning", "end")
            or (value["integrality"] == "complete" and value["retained_portion"] != "unknown")):
        raise ValueError("Complétude ou détérioration du montage invalide.")
    if not isinstance(value["note"], str) or len(value["note"]) > 2000:
        raise ValueError("La note doit contenir au maximum 2 000 caractères.")
    for field in ("source_paths", "affected_source_paths"):
        paths = value[field]
        if (not isinstance(paths, list) or len(paths) > 100
                or any(not isinstance(path, str) or not path.startswith("/") or "\0" in path for path in paths)):
            raise ValueError("Sources de la déclaration invalides.")
    if not set(value["affected_source_paths"]).issubset(value["source_paths"]):
        raise ValueError("La source signalée ne fait pas partie du montage.")
    stamp = value["declared_at"]
    if not isinstance(stamp, str) or datetime.fromisoformat(stamp).tzinfo is None:
        raise ValueError("Date de déclaration invalide.")
    return deepcopy(value)


def declaration(session, *, integrality="complete", damage="none", retained_portion="unknown",
                note="", affected_source_paths=()):
    return checked_condition({"integrality": integrality, "damage": damage,
                              "retained_portion": retained_portion, "note": note,
                              "declared_at": datetime.now(timezone.utc).isoformat(),
                              "source_paths": source_paths(session),
                              "affected_source_paths": list(affected_source_paths)})


def needs_review(session):
    condition = getattr(session, "copy_condition", None)
    return condition is None or checked_condition(condition)["source_paths"] != source_paths(session)
