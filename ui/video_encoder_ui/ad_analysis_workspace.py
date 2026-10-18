"""Keep a known analysis alive until its edited project has been saved."""

import fcntl
import hashlib
import json
import os
import shutil
from pathlib import Path


class AdAnalysisWorkspace:
    LOCK_NAME = ".video-encoder-analysis.lock"
    CONTENTS = {
        "detection", "boundaries", "proposal.json", "proposal.review.json",
        "detection.log", "refinement.log", "proposal.log", LOCK_NAME,
    }

    @classmethod
    def for_report(cls, report, source):
        report, source = Path(report).absolute(), Path(source).resolve()
        root = report.parent.parent
        fingerprint = hashlib.sha256(str(source).encode()).hexdigest()[:12]
        if report.name != "boundary-hypotheses.json" or report.parent.name != "boundaries":
            return None
        if root.name != f"ad-analysis-{fingerprint}":
            return None
        try:
            if any(path.is_symlink() for path in [root, report.parent, report, root / "proposal.json"]):
                return None
            boundary = json.loads(report.read_text(encoding="utf-8"))
            proposal = json.loads((root / "proposal.json").read_text(encoding="utf-8"))
            if boundary.get("format") != "video_encoder.6ter_boundary_hypotheses" or boundary.get("version") != 3:
                return None
            if Path(boundary["source"]).resolve() != source or proposal.get("format") != "video_encoder.trim_project":
                return None
            if not cls.known_contents(root) or source.is_relative_to(root.resolve()):
                return None
            return cls(root)
        except (OSError, ValueError, KeyError, TypeError):
            return None

    @classmethod
    def known_contents(cls, root):
        return all(entry.name in cls.CONTENTS and not entry.is_symlink() for entry in root.iterdir())

    def __init__(self, root):
        self.root = root.resolve()
        stat = self.root.stat()
        self.identity = (stat.st_dev, stat.st_ino)
        self.open_lock()

    def open_lock(self):
        descriptor = os.open(self.root / self.LOCK_NAME, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        self.lock = os.fdopen(descriptor, "r+")
        fcntl.flock(self.lock, fcntl.LOCK_SH | fcntl.LOCK_NB)

    def close(self):
        self.lock.close()

    def __del__(self):
        lock = getattr(self, "lock", None)
        if lock is not None:
            lock.close()

    def clean_after_save(self, destination, sources):
        if not self.root.exists():
            self.close()
            return
        stat = self.root.lstat()
        if self.root.is_symlink() or (stat.st_dev, stat.st_ino) != self.identity:
            raise ValueError(f"Dossier d’analyse remplacé : {self.root}")
        protected = [Path(destination).resolve(), *(Path(source.path).resolve() for source in sources)]
        if any(path.is_relative_to(self.root) for path in protected):
            raise ValueError(f"Le projet ou une source se trouve dans le dossier d’analyse : {self.root}")
        if not self.known_contents(self.root):
            raise ValueError(f"Contenu supplémentaire à conserver dans le dossier d’analyse : {self.root}")
        if self.lock.closed:
            self.open_lock()
        stat = (self.root / self.LOCK_NAME).stat()
        held = os.fstat(self.lock.fileno())
        if (stat.st_dev, stat.st_ino) != (held.st_dev, held.st_ino):
            raise ValueError(f"Verrou d’analyse remplacé : {self.root}")
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.close()
            raise ValueError(f"Analyse encore utilisée par une autre préparation : {self.root}") from None
        shutil.rmtree(self.root)
        self.close()
