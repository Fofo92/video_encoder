"""Prepare source windows selected by decoded frame index, without input seeking.

Research only: FFmpeg decoded indices must still be checked against the editor.
No project is rewritten. An existing output directory is never reused.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def plan(project, radius=250):
    if project.get("format") != "video_encoder.trim_project" or project.get("version") != 2:
        raise ValueError("Expected a version 2 trim project")
    if len(project["sources"]) != 1 or not 1 <= radius <= 1500:
        raise ValueError("Use one source and a window radius of 1 to 1500 frames")
    source = project["sources"][0]
    rows = project["timeline"]
    if not 2 <= len(rows) <= 5:
        raise ValueError("Expected two to five retained segments")
    previous = -1
    for row in rows:
        if (row.get("type") != "segment" or row.get("source_id") != source["id"]
                or type(row.get("start_frame")) is not int or type(row.get("end_frame")) is not int
                or not previous < row["start_frame"] <= row["end_frame"]):
            raise ValueError("Segments must be ordered, disjoint and from the same source")
        previous = row["end_frame"]
    windows = []
    for index, (left, right) in enumerate(zip(rows, rows[1:]), 1):
        for kind, center in [("departure", left["end_frame"] + 1), ("resume", right["start_frame"])]:
            first, end = max(0, center - radius), center + radius
            windows.append({"name": f"{kind}-{index}.mp4", "first_decoded_frame": first,
                            "end_decoded_frame_exclusive": end, "expected_frame_count": end - first,
                            "reviewed_boundary_local_frame": center - first})
    return source["path"], windows


def source_identity(path):
    stat = path.stat()
    return {"bytes": stat.st_size, "inode": stat.st_ino, "device": stat.st_dev,
            "mtime_ns": stat.st_mtime_ns, "ctime_ns": stat.st_ctime_ns}


def export(project_path, output, radius=250):
    encoded = project_path.read_bytes()
    source, windows = plan(json.loads(encoded), radius)
    source = Path(source).resolve(strict=True)
    if not source.is_file():
        raise ValueError("Source must be a regular file")
    identity = source_identity(source)
    metadata = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=avg_frame_rate",
         "-of", "json", str(source)], capture_output=True, text=True, check=True,
    )
    if json.loads(metadata.stdout)["streams"][0]["avg_frame_rate"] != "25/1":
        raise ValueError("This source alignment pilot currently requires 25 average fps")
    output.mkdir(parents=True, exist_ok=False)
    manifest = {"status": "prepared", "source": str(source), "source_identity": identity,
                "reviewed_project_sha256": hashlib.sha256(encoded).hexdigest(), "fps": 25,
                "coordinate_basis": "FFmpeg decoded source frame index, not verified editor frame index",
                "editor_alignment": "requires_visual_verification", "windows": windows}
    manifest_path = output / "frame-map.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    labels = "".join(f"[v{i}]" for i in range(len(windows)))
    filters = [f"[0:v:0]split={len(windows)}{labels}"]
    for index, row in enumerate(windows):
        filters.append(f"[v{index}]trim=start_frame={row['first_decoded_frame']}:"
                       f"end_frame={row['end_decoded_frame_exclusive']},"
                       f"setpts=N/(25*TB),scale=960:-2[out{index}]")
    command = ["ffmpeg", "-nostdin", "-v", "error", "-n", "-i", str(source),
               "-filter_complex_threads", "1", "-filter_complex", ";".join(filters)]
    for index, row in enumerate(windows):
        command += ["-map", f"[out{index}]", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "24",
                    "-fps_mode", "passthrough", str(output / row["name"])]
    with (output / "export.log").open("wb") as log:
        subprocess.run(command, stdout=log, stderr=log, check=True)
    if source_identity(source) != identity:
        raise ValueError("Source changed during extraction; keep diagnostics, do not use these windows")
    for row in windows:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
             "stream=nb_read_frames", "-of", "json", str(output / row["name"])],
            capture_output=True, text=True, check=True,
        )
        count = int(json.loads(result.stdout)["streams"][0]["nb_read_frames"])
        if count != row["expected_frame_count"]:
            raise ValueError("Truncated window; keep diagnostics, do not use this frame map")
    manifest["status"] = "export_complete_editor_alignment_unverified"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--radius", type=int, default=250)
    args = parser.parse_args()
    print(json.dumps(export(args.project, args.output, args.radius), indent=2))
