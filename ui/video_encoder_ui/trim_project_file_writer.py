import json
import os
import stat
import uuid
from pathlib import Path

from .vidb_project_link import VidbProjectLink
from .original_language_review import selection_scope


class TrimProjectFileWriter:
    def __init__(self, bridge, vidb_link=None):
        self.bridge = bridge
        self.vidb_link = vidb_link
        self.vidb_result = {"status": "disabled"}
        self.cleanup_warnings = []

    def save(self, session, path):
        self.cleanup_warnings = []
        document = dict(self.bridge.convert(session))
        document.pop("vidb", None)
        destination = Path(path)
        session.project_id = VidbProjectLink.project_id(session)
        document["project_id"] = session.project_id
        previous = getattr(session, "vidb", {})
        if isinstance(previous, dict) and previous:
            document["vidb"] = {key: value for key, value in previous.items() if key != "metadata"}
        selection = getattr(session, "track_selection", None)
        if isinstance(selection, dict) and selection.get("scope") == selection_scope(document):
            document["track_selection"] = selection

        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        self.write_atomic(destination, text)
        self.vidb_result = self.vidb_link.identify(document, destination) if self.vidb_link else {"status": "disabled"}
        if self.vidb_result.get("status") != "disabled":
            document["vidb"] = {key: value for key, value in self.vidb_result.items() if key != "metadata"}
            session.vidb = document["vidb"]
            if document.get("track_selection", {}).get("scope") != selection_scope(document):
                document.pop("track_selection", None)
                session.track_selection = None
            self.write_atomic(destination, json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        self.clean_analysis(session, destination)

        return destination

    @staticmethod
    def write_atomic(destination, text):
        if destination.is_symlink():
            raise ValueError("Le projet de destination est un lien symbolique.")
        temporary = None
        try:
            temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}"
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                if destination.exists():
                    os.fchmod(file.fileno(), stat.S_IMODE(destination.stat().st_mode))
                file.write(text)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary, destination)
            descriptor = os.open(destination.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def clean_analysis(self, session, destination):
        for workspace in tuple(getattr(session, "analysis_workspaces", ())):
            try:
                workspace.clean_after_save(destination, session.sources)
            except (OSError, ValueError) as error:
                self.cleanup_warnings.append(str(error))
            else:
                session.analysis_workspaces.remove(workspace)
