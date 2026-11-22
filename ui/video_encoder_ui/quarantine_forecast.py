import json
import shutil
import stat
from collections import defaultdict
from datetime import datetime, time, timedelta
from pathlib import Path


def quarantine_forecast(report, now):
    root = Path(report["root"])
    disk = shutil.disk_usage(root)
    device = root.stat().st_dev
    files = {}
    for path in root.rglob("*"):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISREG(info.st_mode) and info.st_dev == device:
            files[path] = info

    eligible = [
        (entry, [files[path]]) for entry in report["entries"]
        if (path := Path(entry["path"])).parent == root and path in files
    ]
    return forecast(disk, sum(info.st_size for info in files.values()), eligible, now)


def project_trash_forecast(report, now, root=Path("/videos")):
    disk = shutil.disk_usage(root)
    device = root.stat().st_dev
    eligible = []
    total = 0
    for entry in report["entries"]:
        directory = Path(entry["directory"])
        if not directory.is_relative_to(root) or directory.stat().st_dev != device:
            continue
        manifest = directory / "manifest.json"
        paths = [Path(path) for path in json.loads(manifest.read_text()).values()]
        sizes = []
        for path in [manifest, *paths]:
            if path.parent != directory:
                raise ValueError(f"Chemin inattendu dans la corbeille : {path}")
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_dev != device:
                raise ValueError(f"Fichier de corbeille inattendu : {path}")
            sizes.append(info)
        total += sum(info.st_size for info in sizes)
        eligible.append((entry, sizes))
    return forecast(disk, total, eligible, now)


def forecast(disk, total, eligible, now):
    # Match the local daily schedule installed by bin/install-quarantine-timer.
    sweep_time = time(3, 30)
    day = timedelta(days=1)
    first = now.date()
    if now.time() >= sweep_time:
        first += day

    batches = defaultdict(list)
    for entry, files in eligible:
        if entry["state"] not in {"scheduled", "due"} or not entry.get("delete_after"):
            continue
        deadline = datetime.fromisoformat(entry["delete_after"].replace("Z", "+00:00")).astimezone()
        sweep = deadline.date()
        if deadline.time() > sweep_time:
            sweep += day
        batches[max(first, sweep)].append(files)

    remaining = total
    free = disk.free
    rows = []
    if batches:
        current = first
        last = max(batches)
        while current <= last:
            batch = batches.get(current, [])
            files = [info for entry_files in batch for info in entry_files]
            removed = sum(info.st_size for info in files)
            remaining -= removed
            free += sum(info.st_blocks * 512 for info in files if info.st_nlink == 1)
            rows.append((current, len(batch), removed, remaining, min(free, disk.total)))
            current += day
    return total, disk, rows
