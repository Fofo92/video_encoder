import json
import os
import stat
import uuid
from pathlib import Path


class TrimProjectFileWriter:
    def __init__(self, bridge):
        self.bridge = bridge
        self.cleanup_warnings = []

    def save(self, session, path):
        self.cleanup_warnings = []
        document = self.bridge.convert(session)
        destination = Path(path)

        text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
        self.write_atomic(destination, text)
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
