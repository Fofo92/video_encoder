"""Prepare a new copy; never edit the source or launch an encoder concurrently."""
from functools import lru_cache
import importlib.util
import json
import os
from pathlib import Path


@lru_cache(maxsize=1)
def pipeline():
    path = Path(__file__).resolve().parents[2] / "lib/video_encoder/copy_version_pipeline.py"
    spec = importlib.util.spec_from_file_location("copy_version_pipeline", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def suggested_output(source):
    source = Path(source)
    stem = source.stem.removesuffix(" - VOST")
    candidate = source.with_name(stem + " - VOST.mkv")
    index = 2
    while candidate.exists() or candidate.is_symlink() or candidate.with_suffix(".json").exists():
        candidate = source.with_name(f"{stem} - VOST {index}.mkv")
        index += 1
    return candidate


def write_new(path, document):
    # Exclusive creation also refuses dangling symlinks.
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def enqueue(document, output, queue):
    source = Path(document["sources"][0]["path"])
    output = Path(output).absolute()
    if output.exists() or output.is_symlink() or output == source or output.suffix.lower() != ".mkv":
        raise ValueError("Choisis une nouvelle destination MKV pour conserver la copie actuelle.")
    project = output.with_suffix(".json")
    write_new(project, document)
    # A failed enqueue leaves the saved project available for retry.
    return queue.enqueue(project, output)
