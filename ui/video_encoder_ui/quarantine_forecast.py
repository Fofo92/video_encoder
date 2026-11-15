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

    # Match the local daily schedule installed by bin/install-quarantine-timer.
    sweep_time = time(3, 30)
    day = timedelta(days=1)
    first = now.date()
    if now.time() >= sweep_time:
        first += day

    batches = defaultdict(list)
    for entry in report["entries"]:
        if entry["state"] not in {"scheduled", "due"} or not entry.get("delete_after"):
            continue
        path = Path(entry["path"])
        if path.parent != root or path not in files:
            continue
        deadline = datetime.fromisoformat(entry["delete_after"].replace("Z", "+00:00")).astimezone()
        sweep = deadline.date()
        if deadline.time() > sweep_time:
            sweep += day
        batches[max(first, sweep)].append(files[path])

    total = remaining = sum(info.st_size for info in files.values())
    free = disk.free
    rows = []
    if batches:
        current = first
        last = max(batches)
        while current <= last:
            batch = batches.get(current, [])
            removed = sum(info.st_size for info in batch)
            remaining -= removed
            free += sum(info.st_blocks * 512 for info in batch if info.st_nlink == 1)
            rows.append((current, len(batch), removed, remaining, min(free, disk.total)))
            current += day
    return total, disk, rows
