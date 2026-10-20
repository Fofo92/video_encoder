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
    if any('family_role' in row for row in rows):
        if any(row.get('family_role') != ('departure' if index % 2 == 0 else 'resume')
               for index, row in enumerate(rows)):
            raise ValueError('Les familles ne forment pas une alternance départ/reprise.')
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


def refinement_problem(rows):
    if not 3 <= len(rows) <= 12:
        return f'{len(rows)} occurrences dans l’œuvre : l’affinement en accepte de 3 à 12. Choisis un autre groupe.'
    if any(left['core_end_seconds'] + 12 > right['core_start_seconds'] for left, right in zip(rows, rows[1:])):
        return 'Les occurrences sont trop proches pour être affinées séparément. Choisis un autre groupe.'
    return None


def support_family_problem(candidate, first, last):
    if candidate.get('grouping') != 'each_occurrence_directly_matches_one_anchor':
        return 'Actualise la découverte depuis son cache pour utiliser deux familles.'
    rows = candidate['occurrences']
    if not 3 <= len(rows) <= 12:
        return 'Il faut de 3 à 12 répétitions dans l’enregistrement pour soutenir cette famille.'
    if not inside_occurrences(candidate, first, last):
        return 'Cette famille ne contient aucune occurrence dans l’œuvre.'
    if any(left['core_end_seconds'] + 20 > right['core_start_seconds'] for left, right in zip(rows, rows[1:])):
        return 'Les fenêtres de cette famille sont trop proches.'
    return None


def pair_problem(report, departure, resume, first, last):
    if report is None or type(departure) is not int or type(resume) is not int:
        return 'Choisis la famille des départs et celle des reprises.'
    if departure == resume:
        return 'Choisis deux familles distinctes.'
    rows, supports = [], []
    for role, index in [('departure', departure), ('resume', resume)]:
        if not 1 <= index <= len(report['candidates']):
            return 'Famille inconnue.'
        candidate = report['candidates'][index - 1]
        problem = support_family_problem(candidate, first, last)
        if problem:
            return problem
        rows.extend((row['core_start_seconds'], role) for row in inside_occurrences(candidate, first, last))
        supports.extend(candidate['occurrences'])
    supports.sort(key=lambda row: row['core_start_seconds'])
    if any(left['core_end_seconds'] + 20 > right['core_start_seconds'] for left, right in zip(supports, supports[1:])):
        return 'Les fenêtres des deux familles se chevauchent.'
    rows.sort()
    if not 2 <= len(rows) <= 12 or len(rows) % 2 or any(role != ('departure' if i % 2 == 0 else 'resume')
                                                       for i, (_, role) in enumerate(rows)):
        return 'Les occurrences dans l’œuvre doivent alterner départ, reprise, puis départ, reprise.'
    return None


def automatic_hypothesis(report, first, last):
    """Prioritise a review hypothesis, never certify advertisements or their absence.

    Repetition support is a search priority, not a calibrated confidence score.
    Exact support ties require arbitration rather than an arbitrary group number.
    """
    if report is None:
        return None, 'Charge ou lance une recherche pour préparer les raccords.'
    if len(report.get('candidates', [])) > 100:
        return None, 'Trop de candidats pour la sélection automatique de ce pilote.'
    choices = []
    candidates = report.get('candidates', [])
    for index, candidate in enumerate(candidates, 1):
        inside = inside_occurrences(candidate, first, last)
        # The common-family extractor currently needs at least three clips.
        if len(inside) == 4 and refinement_problem(inside) is None:
            choices.append({'candidate': index, 'breaks': 2,
                            'support': len(candidate['occurrences'])})
        for other_index, other in enumerate(candidates, 1):
            count = len(inside) + len(inside_occurrences(other, first, last))
            if count in (2, 4) and pair_problem(report, index, other_index, first, last) is None:
                choices.append({'departure': index, 'resume': other_index, 'breaks': count // 2,
                                'support': len(candidate['occurrences']) + len(other['occurrences'])})
    if not choices:
        return None, ('Aucune hypothèse exploitable d’une ou deux plages publicitaires. '
                      'Cela ne prouve pas l’absence de publicité.')
    choices.sort(key=lambda row: -row['support'])
    if len(choices) > 1 and choices[0]['support'] == choices[1]['support']:
        return None, ('Plusieurs hypothèses ont le même soutien : arbitrage nécessaire. '
                      'Aucun découpage n’est choisi automatiquement.')
    result = {**choices[0], 'alternatives': len(choices) - 1,
              'needs_manual_review': True, 'search_partial': bool(report.get('index_limits_reached'))}
    return result, None


def latest_extraction(repository, source, bounds, report_path, choice):
    """Locate compatible extracted windows; the worker rechecks their contents."""
    import hashlib
    import json
    options = dict(zip(choice[::2], choice[1::2]))
    selected = int(options['--candidate']) if '--candidate' in options else None
    families = ({'departure': int(options['--departure-candidate']),
                 'resume': int(options['--resume-candidate'])} if selected is None else None)
    report_hash = hashlib.sha256(Path(report_path).read_bytes()).hexdigest()
    current = identity(source)
    paths = sorted((Path(repository) / 'tmp/repeated-sequence-reviews').glob('*/manifest.json'),
                   key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for path in paths:
        try:
            data = json.loads(path.read_text())
            if (data.get('source') == str(Path(source).resolve()) and data.get('source_identity') == current
                    and data.get('outer_bounds') == list(bounds) and data.get('scan_report_sha256') == report_hash
                    and data.get('selected_candidate') == selected and data.get('selected_families') == families
                    and data.get('windows') and all((path.parent / row['name']).is_file() for row in data['windows'])):
                return path.parent
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return None
