from pathlib import Path

from .vidb_project_link import VidbProjectLink


def project_identification_context(session, source, suggested):
    session.project_id = VidbProjectLink.project_id(session)
    provisional = Path(suggested).with_suffix(".json")
    if not provisional.is_relative_to(Path("/videos")):
        provisional = Path("/videos") / Path(source).with_suffix(".json").name
    sources = getattr(session, "sources", ())
    document = {"version": 2, "project_id": session.project_id, "vidb": getattr(session, "vidb", {}),
                "sources": [{"path": str(item.path), "inspection": getattr(item, "inspection", None)}
                            for item in sources] or [{"path": str(source)}]}
    return document, provisional
