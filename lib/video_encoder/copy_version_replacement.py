"""Reclaim a converted copy's old name, preserving originals and serializing with workers."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import signal
import sys

SUFFIX = ".video_encoder-export.json"
INACTIVE = {"done", "failed", "interrupted"}


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError(f"Fichier JSON absent, trop volumineux ou non régulier : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def signature(path):
    stat = path.stat()
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Fichier non régulier : {path}")
    return dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns, inode=stat.st_ino, device=stat.st_dev)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_new(path, data):
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def paths_for(project, directory, name):
    if (not name or name != name.strip() or Path(name).name != name
            or any(ord(char) < 32 for char in name) or "\\" in name
            or name.endswith((".json", ".mkv", ".mp4", ".m4v"))):
        raise ValueError("Nom de projet invalide.")
    target = directory / (name + ".json")
    if project.parent != directory or target == project:
        raise ValueError("Remplace la version dans son dossier actuel, avec un nom différent.")
    return target, target.with_suffix(".mkv")


def preparation(project, directory, name):
    target_project, target_video = paths_for(project, directory, name)
    document = read_json(project)
    video = project.with_suffix(".mkv")
    receipt_path = Path(str(video) + SUFFIX)
    receipt = read_json(receipt_path)
    change = document.get("version_change", {})
    valid = (document.get("format") == "video_encoder.copy_version" and document.get("version") == 2
             and change.get("profile") == "VOST" and change.get("source_path") == str(target_video)
             and document.get("sources") == [{"id": "copy", "path": str(target_video)}]
             and change.get("original_confirmed") is True and change.get("burned_french_confirmed") is True
             and receipt.get("format") == "video_encoder.completed_export" and receipt.get("version") == 1
             and receipt.get("project_path") == str(project) and receipt.get("output_path") == str(video)
             and receipt.get("project_sha256") == digest(project.read_bytes())
             and receipt.get("version_change") == change and receipt.get("roles") == ["original"]
             and receipt.get("project_id") == document.get("project_id")
             and receipt.get("vidb") == document.get("vidb"))
    if not valid:
        raise ValueError("Le reçu ne prouve pas un changement VOST terminé depuis cette ancienne copie.")
    current = signature(video)
    modified = datetime.fromisoformat(receipt["modified_at"].replace("Z", "+00:00"))
    micros = int(modified.timestamp()) * 1_000_000 + modified.microsecond
    if receipt.get("byte_size") != current["size"] or micros != video.stat().st_mtime_ns // 1000:
        raise ValueError("La copie VOST a changé depuis son export.")
    old_receipt = Path(str(target_video) + SUFFIX)
    old_files = []
    project_bytes = None
    if target_project.exists() or target_project.is_symlink():
        old_document = read_json(target_project)
        if old_document.get("format") not in {
                "video_encoder.trim_project", "video_encoder.dvd_project", "video_encoder.copy_version"}:
            raise ValueError("L’ancien projet n’est pas un projet video_encoder reconnu.")
        project_bytes = target_project.read_bytes()
        old_files.append(target_project)
    if target_video.exists() or target_video.is_symlink():
        if signature(target_video) != change.get("identity"):
            raise ValueError("L’ancienne vidéo diffère de la source utilisée pour produire la VOST.")
        old_files.append(target_video)
    if old_receipt.exists() or old_receipt.is_symlink():
        old = read_json(old_receipt)
        if old.get("project_path") != str(target_project) or old.get("output_path") != str(target_video):
            raise ValueError("Le reçu de l’ancienne copie ne correspond pas à ces chemins.")
        old_files.append(old_receipt)
    if project_bytes is None:
        validate_missing_project(old_receipt, target_video, old_files, document)
    project_sha = digest(project_bytes) if project_bytes is not None else read_json(old_receipt)["project_sha256"]
    for path in (project, target_project):
        workspace = path.with_name("video_encoder_" + path.stem + "_workspace")
        if workspace.exists() or workspace.is_symlink():
            raise ValueError(f"Un dossier de travail subsiste : {workspace}")
    trash = directory / ".video_encoder_trash"
    if trash.is_symlink():
        raise ValueError("La corbeille des projets ne peut pas être un lien symbolique.")
    key = digest(project.read_bytes() + receipt_path.read_bytes() + project_sha.encode("ascii"))[:24]
    archive = trash / ("version-" + key)
    if archive.exists() or archive.is_symlink():
        raise ValueError(f"Une archive de remplacement existe déjà : {archive}")
    return dict(project=project, video=video, receipt_path=receipt_path, document=document,
                receipt=receipt, change=change, target_project=target_project, target_video=target_video,
                archive=archive, old_files=old_files,
                project_missing=project_bytes is None, source_project_sha=project_sha,
                source_missing=target_video not in old_files)


def validate_missing_project(receipt_path, video, old_files, document):
    if video not in old_files or receipt_path not in old_files:
        raise ValueError("Ancien JSON absent : la vidéo initiale et son reçu sont nécessaires au remplacement.")
    receipt = read_json(receipt_path)
    sha = receipt.get("project_sha256", "")
    modified = datetime.fromisoformat(receipt.get("modified_at", "").replace("Z", "+00:00"))
    micros = int(modified.timestamp()) * 1_000_000 + modified.microsecond
    record_id = document.get("vidb", {}).get("record_id")
    valid = (receipt.get("format") == "video_encoder.completed_export" and receipt.get("version") == 1
             and isinstance(sha, str) and len(sha) == 64 and all(c in "0123456789abcdef" for c in sha)
             and receipt.get("byte_size") == video.stat().st_size
             and micros == video.stat().st_mtime_ns // 1000
             and record_id is not None and receipt.get("vidb", {}).get("record_id") == record_id)
    if not valid:
        raise ValueError("Ancien JSON absent : le reçu ne prouve pas l’identité de la vidéo initiale et de sa fiche.")


def check_jobs(db, state):
    rows = [dict(row) for row in db.execute("SELECT * FROM jobs")]
    own = [r for r in rows if r.get("project_path") == str(state["project"])]
    old = [r for r in rows if r.get("project_path") == str(state["target_project"])]
    if not any(r["status"] == "done" for r in own) or any(r["status"] not in INACTIVE for r in own):
        raise ValueError("Le changement de version doit être terminé avant de remplacer l’ancienne copie.")
    if any(r["status"] not in INACTIVE for r in old):
        raise ValueError("Une tâche utilise encore l’ancien projet.")
    exempt = {r["id"] for r in own + old}
    for row in rows:
        if row["id"] in exempt:
            continue
        if row.get("output_path") in {str(state["target_video"]), str(state["video"])}:
            raise ValueError("Une autre tâche réserve une de ces vidéos.")
        path = Path(row["project_path"]) if row.get("project_path") else None
        if path and path.is_file():
            doc = read_json(path)
            if not isinstance(doc, dict):
                raise ValueError(f"Préparation illisible : {path}")
            items = doc.get("timeline" if doc.get("version") == 1 else "sources", [])
            if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
                raise ValueError(f"Sources de préparation invalides : {path}")
            references = [r.get("source" if doc.get("version") == 1 else "path") for r in items]
            if str(state["target_video"]) in references or str(state["video"]) in references:
                raise ValueError(f"Une autre préparation utilise cette copie : {path}")
    return own, old


def archived(state, path):
    prefix = "0-" if path == state["target_project"] else "1-"
    return state["archive"] / (prefix + path.name)


def plan(state):
    archive = state["archive"]
    files = [{"source": str(path), "destination": str(archived(state, path))} for path in state["old_files"]]
    for source, target in [(state["project"], state["target_project"]),
                           (state["video"], state["target_video"]),
                           (state["receipt_path"], Path(str(state["target_video"]) + SUFFIX))]:
        files.append({"source": str(source), "destination": str(target)})
    return {"format": "video_encoder.project_relocation", "version": 1,
            "project_path": str(state["target_project"]), "files": files,
            "outputs": [str(state["target_video"])]}


def final_documents(state):
    archive_source = archived(state, state["target_video"])
    document = json.loads(json.dumps(state["document"]))
    document["sources"][0]["path"] = str(archive_source)
    document["version_change"]["source_path"] = str(archive_source)
    project_bytes = encoded(document)
    receipt = json.loads(json.dumps(state["receipt"]))
    receipt.update(project_path=str(state["target_project"]), output_path=str(state["target_video"]),
                   previous_output_path=str(state["video"]), project_sha256=digest(project_bytes),
                   version_change=document["version_change"])
    receipt.get("probe", {}).get("format", {})["filename"] = str(state["target_video"])
    receipt["copy_version_replacement"] = {
        "source_path": str(state["target_video"]), "archived_source_path": str(archive_source),
        "archive_directory": str(state["archive"]), "source_identity": state["change"]["identity"],
        "source_missing_before_replacement": state["source_missing"],
        "archived_project_path": str(archived(state, state["target_project"])),
        "source_project_sha256": state["source_project_sha"],
        "replaced_at": datetime.now(timezone.utc).isoformat()}
    if state["project_missing"]:
        receipt["copy_version_replacement"]["source_project_missing_before_replacement"] = True
    return project_bytes, encoded(receipt)


def apply(db, state, own, old):
    snapshots = {p: signature(p) for p in state["old_files"] +
                 [state["project"], state["video"], state["receipt_path"]]}
    project_bytes, receipt_bytes = final_documents(state)
    moved, created = [], []
    made_archive = False
    archive = state["archive"]
    try:
        archive.parent.mkdir(mode=0o700, exist_ok=True)
        archive.mkdir(mode=0o700)
        made_archive = True
        manifest = {str(p): str(archived(state, p)) for p in state["old_files"]}
        write_new(archive / "manifest.json", encoded(manifest))
        for source in state["old_files"]:
            if signature(source) != snapshots[source]:
                raise ValueError(f"Fichier modifié pendant la préparation : {source}")
            destination = archived(state, source)
            os.rename(source, destination)
            moved.append((source, destination))
        for target, data in [(state["target_project"], project_bytes),
                             (Path(str(state["target_video"]) + SUFFIX), receipt_bytes)]:
            with target.open("xb") as stream:
                created.append(target)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        os.link(state["video"], state["target_video"])
        created.append(state["target_video"])
        for path in (state["project"], state["video"], state["receipt_path"]):
            if signature(path) != snapshots[path]:
                raise ValueError(f"Copie VOST modifiée pendant le remplacement : {path}")
        for source, destination in moved:
            if signature(destination) != snapshots[source]:
                raise ValueError("Une ancienne copie a changé pendant l’archivage.")
        db.execute("CREATE TABLE IF NOT EXISTS project_trash_roots (path TEXT PRIMARY KEY)")
        db.execute("INSERT OR IGNORE INTO project_trash_roots(path) VALUES (?)", (str(archive.parent),))
        for row in old:
            output = str(archived(state, state["target_video"])) if row.get("output_path") else None
            if row.get("output_path") and row["output_path"] != str(state["target_video"]):
                raise ValueError("L’ancien projet possède une autre sortie : remplace ses copies séparément.")
            db.execute("UPDATE jobs SET project_path=?, output_path=? WHERE id=?",
                       (str(archived(state, state["target_project"])), output, row["id"]))
        for row in own:
            if row.get("output_path") != str(state["video"]):
                raise ValueError("Le projet VOST possède plusieurs sorties distinctes.")
            db.execute("UPDATE jobs SET project_path=?, output_path=? WHERE id=?",
                       (str(state["target_project"]), str(state["target_video"]), row["id"]))
        db.commit()
    except BaseException:
        db.rollback()
        for path in reversed(created):
            path.unlink()
        for source, destination in reversed(moved):
            os.rename(destination, source)
        if made_archive:
            (archive / "manifest.json").unlink(missing_ok=True)
            archive.rmdir()
        raise
    # As with regular relocation, don't delete any old path modified after commit.
    for path in (state["project"], state["video"], state["receipt_path"]):
        try:
            if signature(path) == snapshots[path]:
                path.unlink()
        except OSError as error:
            print(f"Remplacement terminé ; ancien chemin conservé : {path} ({error})", file=sys.stderr)
    return str(state["target_project"])


def replace(database, project, directory, name, *, preview=False):
    with sqlite3.connect(database, timeout=10) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        state = preparation(Path(project).absolute(), Path(directory).resolve(), name)
        own, old = check_jobs(db, state)
        if preview:
            db.rollback()
            return plan(state)
        return apply(db, state, own, old)


if __name__ == "__main__":
    def interrupted(_signal, _frame):
        raise InterruptedError("Remplacement interrompu ; restauration des chemins en cours.")

    signal.signal(signal.SIGTERM, interrupted)
    try:
        if len(sys.argv) != 6 or sys.argv[5] not in ("preview", "apply"):
            raise ValueError("Arguments de remplacement invalides.")
        print(json.dumps(replace(*sys.argv[1:5], preview=sys.argv[5] == "preview"), ensure_ascii=False))
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
