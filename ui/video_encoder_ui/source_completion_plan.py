import json
import stat
from dataclasses import dataclass
from pathlib import Path


class SourceCompletionError(RuntimeError):
    pass


def file_identity(path):
    observed = Path(path).lstat()
    if not stat.S_ISREG(observed.st_mode) or observed.st_size <= 0:
        raise SourceCompletionError(f"Fichier absent, vide ou non régulier : {path}")
    return observed.st_dev, observed.st_ino, observed.st_size, observed.st_mtime_ns


def project_sources(path):
    path = Path(path)
    if path.stat().st_size > 2 * 1024 * 1024:
        raise SourceCompletionError(f"Projet trop volumineux : {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != "video_encoder.trim_project":
        raise SourceCompletionError(f"Format de projet inconnu : {path}")
    if document.get("version") == 1:
        paths = [item["source"] for item in document["timeline"] if item.get("type") == "segment"]
    elif document.get("version") == 2:
        paths = [item["path"] for item in document["sources"]]
    else:
        raise SourceCompletionError(f"Version de projet inconnue : {path}")
    if not paths or any(not isinstance(item, str) or not Path(item).is_absolute() for item in paths):
        raise SourceCompletionError(f"Sources de projet invalides : {path}")
    return tuple(dict.fromkeys(Path(item).resolve() for item in paths))


@dataclass(frozen=True)
class CompletedSource:
    source: Path
    identity: tuple
    jobs: tuple
    outputs: tuple


class SourceCompletionPlan:
    def __init__(self, capture_root="/commun/to_be_cut"):
        self.capture_root = Path(capture_root).resolve()

    def collect(self, jobs):
        completed, blocked = {}, set()
        for job in jobs:
            if job.get("kind") != "trim_export":
                continue
            try:
                sources = project_sources(job["input_path"])
            except (OSError, ValueError, KeyError, TypeError, AttributeError, SourceCompletionError) as error:
                if job.get("status") in {"queued", "running", "deferred"}:
                    raise SourceCompletionError(f"Montage non terminé illisible ; sources conservées : {error}") from error
                continue
            if job.get("status") != "done":
                blocked.update(sources)
                continue
            for source in sources:
                completed.setdefault(source, []).append(job)
        return [case for source, entries in completed.items()
                if source not in blocked and (case := self.completed_source(source, entries)) is not None]

    def completed_source(self, source, jobs):
        if not source.is_relative_to(self.capture_root) or source.suffix.lower() not in {".m2t", ".mts", ".ts"}:
            return None
        try:
            identity = file_identity(source)
            outputs = tuple(sorted((job["output_path"], file_identity(job["output_path"])) for job in jobs))
        except (OSError, KeyError, TypeError, SourceCompletionError):
            return None
        return CompletedSource(source, identity, tuple(jobs), outputs)

    def validate(self, case, jobs):
        current = next((item for item in self.collect(jobs) if item.source == case.source), None)
        if current is None or current.identity != case.identity or current.outputs != case.outputs:
            raise SourceCompletionError("La source, les sorties ou la file ont changé. La source est conservée.")
        return current
