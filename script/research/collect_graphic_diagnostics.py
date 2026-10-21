"""Collect existing graphic-review reports without opening the recording."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def discovery_cache(root, source, identity):
    """Find a sealed low-resolution cache without probing the original recording."""
    paths=sorted(root.rglob('manifest.json'),key=lambda path:path.stat().st_mtime_ns,reverse=True)
    for path in paths:
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        try:
            if path.stat().st_size>2*1024*1024:continue
            encoded=path.read_bytes();manifest=json.loads(encoded)
            if (not isinstance(manifest,dict) or manifest.get('status')!='completed'
                    or manifest.get('source')!=str(source) or manifest.get('source_identity')!=identity):
                continue
            count=manifest.get('sampled_frames')
            if type(count) is not int or not 0<count<=108000 or not manifest.get('cache_sha256'):
                continue
            cache=Path(manifest.get('cache_path',path.parent/'sampled-rgb.bin'))
            if (cache.is_symlink() or not cache.resolve(strict=True).is_relative_to(root)
                    or cache.stat().st_size!=count*1728):
                continue
            pixels=cache.read_bytes()
            if hashlib.sha256(pixels).hexdigest()!=manifest['cache_sha256']:
                continue
            if path.read_bytes()!=encoded:
                raise ValueError('Discovery manifest changed during collection')
            return encoded,pixels
        except (OSError,ValueError,TypeError):
            continue
    raise ValueError('Aucun cache de découverte complet et vérifié trouvé ; aucun décodage relancé.')


def collect(root, source, output, include_review_clips=False, include_discovery_cache=False):
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
    pipeline_path = max(matches)[1]
    pipeline_bytes = pipeline_path.read_bytes()
    pipeline = json.loads(pipeline_bytes)
    directory = pipeline_path.parent
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
    if include_review_clips:
        for field, folder in [('observation_manifest', 'observations'), ('review_manifest', 'native-review')]:
            manifest_path = Path(pipeline[field])
            if not manifest_path.is_absolute():
                raise ValueError('Expected an absolute extraction manifest path')
            if manifest_path.is_symlink() or not manifest_path.resolve(strict=True).is_relative_to(root):
                raise ValueError('Extraction manifest escapes the diagnostic root')
            if manifest_path.stat().st_size > 2 * 1024 * 1024:
                raise ValueError('Oversized extraction manifest')
            encoded = manifest_path.read_bytes()
            expected = pipeline.get(field + '_sha256')
            if expected and hashlib.sha256(encoded).hexdigest() != expected:
                raise ValueError('Extraction manifest differs from the completed calculation')
            manifest = json.loads(encoded)
            if (manifest.get('source') != str(source)
                    or manifest.get('source_identity') != pipeline.get('source_identity')
                    or not isinstance(manifest.get('windows'), list)
                    or not 2 <= len(manifest['windows']) <= 12):
                raise ValueError('Extraction manifest does not match this recording')
            snapshots.append((folder + '/frame-map.json', encoded))
            seen = set()
            for row in manifest['windows']:
                name = row['name']
                if (not isinstance(name, str) or Path(name).name != name
                        or Path(name).suffix.lower() != '.mp4' or name in seen):
                    raise ValueError('Invalid or repeated review clip name')
                seen.add(name)
                path = manifest_path.parent / name
                if path.is_symlink() or path.resolve(strict=True).parent != manifest_path.parent.resolve():
                    raise ValueError('Review clip escapes its extraction directory')
                if path.stat().st_size > 64 * 1024 * 1024:
                    raise ValueError('Review clip exceeds 64 MiB')
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != row.get('sha256'):
                    raise ValueError('Review clip differs from its verified extraction')
                total += len(data)
                if total > 256 * 1024 * 1024:
                    raise ValueError('Review clip collection exceeds 256 MiB')
                snapshots.append((folder + '/' + name, data))
            if manifest_path.read_bytes() != encoded:
                raise ValueError('Extraction manifest changed during collection')
    if include_discovery_cache:
        manifest,pixels=discovery_cache(root,source,pipeline.get('source_identity'))
        total+=len(manifest)+len(pixels)
        if total>256*1024*1024:
            raise ValueError('Combined diagnostics exceed 256 MiB')
        snapshots.extend([('discovery-cache/manifest.json',manifest),
                          ('discovery-cache/sampled-rgb.bin',pixels)])
    if pipeline_path.read_bytes() != pipeline_bytes:
        raise ValueError('Calculation changed during collection; retry after completion')
    index = {'source': str(source), 'run_directory': str(directory),
             'existing_review_clips_included': include_review_clips,
             'existing_discovery_cache_included': include_discovery_cache,
             'recording_opened': False, 'calculation_started': False,
             'files': [{'name': name, 'sha256': hashlib.sha256(data).hexdigest()}
                       for name, data in snapshots]}
    # Build from captured bytes: never include the recording or encoding workspace.
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
    parser.add_argument('--include-review-clips', action='store_true',
                        help='Include only existing, hashed observation and native-review MP4 clips')
    parser.add_argument('--include-discovery-cache', action='store_true',
                        help='Include only an existing sealed low-resolution discovery cache')
    args = parser.parse_args()
    print(collect(args.root, args.source, args.output, args.include_review_clips,
                  args.include_discovery_cache).resolve())
