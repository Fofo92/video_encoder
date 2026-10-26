from PySide6 import QtWidgets

from .vidb_modal_browser import open_vidb_modal, trace_vidb
from .vidb_project_context import project_identification_context
from .vidb_project_link import VidbProjectLink


def review_montage_identification(parent, session, source, suggested, writer):
    """Review the open montage without requiring a saved project or enqueuing it."""
    trace_vidb("manual identification requested")
    link = getattr(writer, "vidb_link", None)
    if not isinstance(link, VidbProjectLink) or session is None:
        QtWidgets.QMessageBox.information(parent, "Identification dans vidb",
                                          "La passerelle vidb n’est pas configurée pour ce montage.")
        return False
    document, provisional = project_identification_context(session, source, suggested)
    result = link.identify(document, provisional, refresh=True)
    writer.vidb_result = result
    status = result.get("status")
    if status in {"identified", "unmatched", "needs_review", "pending", "disabled"}:
        trace_vidb("bridge status=" + status)
    url = result.get("review_url")
    if not url:
        messages = {
            "disabled": "La passerelle vidb est désactivée ou sa configuration est absente.",
            "pending": "vidb est indisponible. Ton montage reste ouvert ; réessaie l’identification.",
            "identified": "La fiche est identifiée, mais vidb ne fournit pas de lien de consultation."
        }
        QtWidgets.QMessageBox.information(parent, "Identification dans vidb",
                                          messages.get(result.get("status"), "vidb n’a fourni aucune proposition."))
        return False
    if not open_vidb_modal(parent, url):
        return False
    # Keep the same identity for later save/export, including an unsaved montage.
    result = link.identify(document, provisional, refresh=True)
    writer.vidb_result = result
    if result.get("status") == "identified":
        session.vidb = {key: value for key, value in result.items() if key != "metadata"}
    return True
