"""Review discovered motifs and explicitly confirmed alternating separators."""
import math
from pathlib import Path

from .trim_session import TrimSession, SourceReference, SegmentSelection


def identity(path):
    stat = Path(path).stat()
    return {'bytes': stat.st_size, 'inode': stat.st_ino, 'device': stat.st_dev,
            'mtime_ns': stat.st_mtime_ns, 'ctime_ns': stat.st_ctime_ns}


def check_source(report, source):
    if report.get('status') != 'experimental' or Path(report['source']).resolve() != Path(source).resolve():
        raise ValueError('Le rapport ne concerne pas la source ouverte.')
    if report.get('source_identity') != identity(source):
        raise ValueError('La source a changé depuis la recherche.')


def inside_occurrences(candidate, first, last):
    rows = candidate['occurrences']
    for row in rows:
        start, end = row['core_start_seconds'], row['core_end_seconds']
        if not all(type(value) in (int, float) and math.isfinite(value) for value in [start, end]) or not 0 <= start < end:
            raise ValueError('Positions de motif invalides.')
    return [row for row in rows if first <= row['core_start_seconds'] * 25
            and row['core_end_seconds'] * 25 <= last + 1]


def proposed_session(report, source, first, last, confirmed=False):
    check_source(report, source)
    if not confirmed:
        raise ValueError('Confirme le sens des séparateurs avant de charger les segments.')
    if report.get('outer_bounds') != [first, last] or report.get('refinement', {}).get('status') != 'experimental':
        raise ValueError('Affinement ou bornes extérieures incompatibles.')
    if report.get('coordinate_basis') != 'FFmpeg decoded source frame index; editor mapping unverified':
        raise ValueError('Les coordonnées du rapport ne sont pas des indices décodés.')
    rows = report['source_motif_limits']
    if not 2 <= len(rows) <= 12 or len(rows) % 2:
        raise ValueError('Il faut un nombre pair de séparateurs : départ, reprise, puis éventuellement départ, reprise.')
    previous = first
    for row in rows:
        start, end = row['motif_start_decoded_frame'], row['motif_end_decoded_frame_exclusive']
        if type(start) is not int or type(end) is not int or not previous < start < end <= last:
            raise ValueError('Limites de motifs invalides ou chevauchantes.')
        previous = end
    session = TrimSession()
    session.add_source(SourceReference('source', Path(source)))
    beginning = first
    for departure, resume in zip(rows[::2], rows[1::2]):
        session.add_segment(SegmentSelection('source', beginning, departure['motif_start_decoded_frame'] - 1))
        beginning = resume['motif_end_decoded_frame_exclusive']
    session.add_segment(SegmentSelection('source', beginning, last))
    return session


def latest_discovery(repository, source):
    """Find an existing result for this unchanged source; never pick a group."""
    import json
    candidates = sorted((Path(repository) / 'tmp').glob('**/resultat.json'),
                        key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for path in candidates:
        try:
            report = json.loads(path.read_text())
            if isinstance(report.get('candidates'), list) and report.get('sample_fps') == 5:
                check_source(report, source)
                return path
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None
