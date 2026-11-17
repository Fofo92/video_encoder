"""Lossless VOST preparation and export, executed by the existing serial queue."""
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
from datetime import datetime, timezone

FORMAT = "video_encoder.copy_version"


def probe(path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def identity(path):
    stat = Path(path).stat()
    if not Path(path).is_file() or Path(path).is_symlink():
        raise ValueError("La copie source doit être un fichier ordinaire, sans lien symbolique.")
    return dict(size=stat.st_size, mtime_ns=stat.st_mtime_ns, inode=stat.st_ino, device=stat.st_dev)


def video_stream(details):
    return next(row for row in details["streams"] if row["codec_type"] == "video"
                and not row.get("disposition", {}).get("attached_pic"))


def prepare(source, audio_index, *, original_confirmed, burned_french_confirmed, details=None):
    if original_confirmed is not True or burned_french_confirmed is not True:
        raise ValueError("Confirme la VO à l’écoute et les sous-titres français incrustés.")
    source = Path(source).absolute()
    signature = identity(source)
    details = details or probe(source)
    audio = next((row for row in details["streams"] if row["index"] == audio_index
                  and row["codec_type"] == "audio"), None)
    if audio is None or audio.get("disposition", {}).get("visual_impaired"):
        raise ValueError("Choisis une piste audio originale exploitable.")
    if signature != identity(source):
        raise ValueError("La copie source a changé pendant son inspection.")
    return {"format": FORMAT, "version": 2, "project_id": str(uuid.uuid4()),
            "sources": [{"id": "copy", "path": str(source)}],
            "version_change": {"profile": "VOST", "source_path": str(source), "identity": signature,
                               "video_index": video_stream(details)["index"], "audio_index": audio_index,
                               "original_confirmed": True, "burned_french_confirmed": True,
                               "confirmed_at": datetime.now(timezone.utc).isoformat()}}


def validate(document, output):
    change = document["version_change"]
    source = Path(document["sources"][0]["path"])
    if (document.get("format") != FORMAT or document.get("version") != 2
            or len(document["sources"]) != 1 or change.get("profile") != "VOST"
            or change.get("source_path") != str(source) or not source.is_absolute()
            or change.get("original_confirmed") is not True or change.get("burned_french_confirmed") is not True
            or any(type(change.get(key)) is not int or change[key] < 0 for key in ("video_index", "audio_index"))):
        raise ValueError("Projet de changement de version invalide.")
    if source == output.absolute() or output.suffix.lower() != ".mkv":
        raise ValueError("Choisis une nouvelle destination MKV.")
    if change["identity"] != identity(source):
        raise ValueError("La copie source a changé : prépare à nouveau le changement de version.")
    details = probe(source)
    streams = {row["index"]: row["codec_type"] for row in details["streams"]}
    if streams.get(change["video_index"]) != "video" or streams.get(change["audio_index"]) != "audio":
        raise ValueError("Les pistes sélectionnées ne sont plus présentes.")
    return source, change, details


def export(project, output, workspace):
    document = json.loads(Path(project).read_text(encoding="utf-8"))
    output = Path(output)
    source, change, before = validate(document, output)
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    staging = workspace / ("version-" + uuid.uuid4().hex + ".mkv")
    subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-v", "error", "-n", "-i", str(source),
                    "-map", "0:" + str(change["video_index"]), "-map", "0:" + str(change["audio_index"]),
                    "-map_metadata", "0", "-map_chapters", "0", "-c", "copy",
                    "-metadata:s:a:0", "language=qaa", "-metadata:s:a:0", "title=Version originale",
                    "-disposition:a:0", "default", str(staging)], check=True)
    after = probe(staging)
    types = [row["codec_type"] for row in after["streams"]]
    if types.count("video") != 1 or types.count("audio") != 1 or types.count("subtitle") != 0:
        raise ValueError("Les pistes finales ne correspondent pas à la VOST demandée.")
    if abs(float(before["format"]["duration"]) - float(after["format"]["duration"])) > 1:
        raise ValueError("La durée finale diffère de celle de la copie source.")
    if change["identity"] != identity(source):
        raise ValueError("La copie source a changé pendant le traitement.")
    # Atomic, no-clobber publication on the output filesystem; preserve failed workspaces.
    os.link(staging, output)
    staging.unlink()
    try:
        workspace.rmdir()
    except OSError:
        pass


if __name__ == "__main__":
    try:
        if len(sys.argv) != 5 or sys.argv[1] != "export":
            raise ValueError("Usage: copy_version_pipeline.py export project output workspace")
        export(*sys.argv[2:])
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
