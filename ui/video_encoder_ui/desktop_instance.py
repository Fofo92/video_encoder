"""Read-only detection of older desktop instances without a launch inbox."""
import os
from pathlib import Path


def other_application_pids(proc=Path("/proc"), *, own_pid=None, uid=None):
    own_pid = os.getpid() if own_pid is None else own_pid
    uid = os.getuid() if uid is None else uid
    result = []
    try:
        entries = list(Path(proc).iterdir())
    except OSError:
        return result
    for entry in entries:
        if not entry.name.isdecimal() or int(entry.name) == own_pid:
            continue
        try:
            if entry.stat().st_uid != uid:
                continue
            arguments = (entry / "cmdline").read_bytes().split(b"\0")
            if any(first == b"-m" and second == b"video_encoder_ui.application"
                   for first, second in zip(arguments, arguments[1:])):
                result.append(int(entry.name))
        except OSError:
            continue
    return sorted(result)
