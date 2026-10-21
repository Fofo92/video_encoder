"""Collect existing graphic-review reports without opening the recording."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def collect(root, source, output):
    root = Path(root).resolve(strict=True)
    matches = []
    for path in root.rglob('pipeline.json'):
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        try:
            if path.stat().st_size > 2 * 1024 * 1024:
                continue
            report = json.loads(path.read_text())
            if isinstance(report, dict) and report.get('source') == str(source):
                matches.append((path.stat().st_mtime_ns, path))
        except (OSError, ValueError):
            continue
    if not matches:
        raise ValueError('Aucun pipeline graphique trouvé pour cette source ; aucun calcul relancé.')
    directory = max(matches)[1].parent
    snapshots = []
    total = 0
    for path in sorted(directory.rglob('*')):
        if path.suffix.lower() not in ('.json', '.log', '.txt') or not path.is_file():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(directory.resolve()):
            raise ValueError('Diagnostic path escapes the selected run')
        before = path.stat()
        if before.st_size > 2 * 1024 * 1024:
            raise ValueError('Diagnostic file exceeds 2 MiB; nothing archived')
        encoded = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError('Diagnostic changed during collection; retry after calculation')
        total += len(encoded)
        if total > 20 * 1024 * 1024 or len(snapshots) >= 500:
            raise ValueError('Diagnostic collection exceeds its bounded size')
        snapshots.append((str(path.relative_to(directory)), encoded))
    index = {'source': str(source), 'run_directory': str(directory),
             'recording_opened': False, 'calculation_started': False,
             'files': [{'name': name, 'sha256': hashlib.sha256(data).hexdigest()}
                       for name, data in snapshots]}
    # Build from captured bytes: no source, clip, workspace or live file handles.
    snapshots.append(('collection.json', (json.dumps(index, indent=2) + '\n').encode()))
    output = Path(output)
    with output.open('xb') as stream:
        with tarfile.open(fileobj=stream, mode='w:gz') as archive:
            for name, encoded in snapshots:
                info = tarfile.TarInfo('graphic-diagnostics/' + name)
                info.size = len(encoded)
                archive.addfile(info, io.BytesIO(encoded))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2] / 'tmp')
    parser.add_argument('--source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(collect(args.root, args.source, args.output).resolve())
