"""Refine explicitly chosen departure/resume families with outside support."""
import math

from repeated_visual_sequences import discover
from repeated_sequence_boundaries import refine
from direct_clip_motifs import discover as direct_discover
from inspect_graphic_motif_context import graphic_context


def plan_pair(report, departure, resume, first, last):
    if report.get('status') != 'experimental' or report.get('sample_fps') != 5 or not 0 <= first < last:
        raise ValueError('Invalid discovery report or outer bounds')
    if departure == resume:
        raise ValueError('Departure and resume must use different families')
    windows = []
    for role, index in [('departure', departure), ('resume', resume)]:
        if type(index) is not int or not 1 <= index <= len(report['candidates']):
            raise ValueError('Choose both departure and resume families explicitly')
        candidate = report['candidates'][index - 1]
        if candidate.get('grouping') != 'each_occurrence_directly_matches_one_anchor':
            raise ValueError('Refresh discovery from its cache before combining families')
        rows = candidate['occurrences']
        if not 3 <= len(rows) <= 12:
            raise ValueError('Each family needs three to twelve support occurrences in the recording')
        inside = 0
        for row in rows:
            start, end = row['core_start_seconds'], row['core_end_seconds']
            if not all(type(value) in (int, float) and math.isfinite(value) for value in [start, end]) or not 0 <= start < end:
                raise ValueError('Invalid motif coordinates')
            is_inside = first <= start * 25 and end * 25 <= last + 1
            inside += is_inside
            windows.append({'name': f'{role}-{len(windows) + 1}.mp4', 'family_role': role,
                            'candidate_index': index, 'inside_coarse_bounds': is_inside,
                            'first_decoded_frame': max(0, round(start * 25) - 250),
                            'end_decoded_frame_exclusive': round(end * 25) + 250,
                            'scanner_core_start_seconds': start})
        if not inside:
            raise ValueError('Both families must have an occurrence inside the work')
    windows.sort(key=lambda row: row['first_decoded_frame'])
    if any(left['end_decoded_frame_exclusive'] > right['first_decoded_frame']
           for left, right in zip(windows, windows[1:])):
        raise ValueError('Support windows overlap; choose distinct unambiguous families')
    inside_roles = [row['family_role'] for row in windows if row['inside_coarse_bounds']]
    if not 2 <= len(inside_roles) <= 12 or len(inside_roles) % 2 or any(
            role != ('departure' if index % 2 == 0 else 'resume') for index, role in enumerate(inside_roles)):
        raise ValueError('The selected internal occurrences do not alternate departure then resume')
    return windows


def graphic_family(features, windows, reason):
    """A reviewed graphical fallback, not separator classification."""
    candidates = direct_discover([value[::5] for value in features])
    if len(candidates) != 1:
        return {'status': 'unavailable', 'reason': reason}
    occurrences = []
    for core in candidates[0]['occurrences']:
        index = core['clip_index']
        if not windows[index].get('inside_coarse_bounds'):
            continue
        context = graphic_context(features[index], round(core['core_start_seconds'] * 25),
                                  round(core['core_end_seconds'] * 25))
        if context['status'] != 'experimental':
            return {'status': 'unavailable', 'reason': context['reason']}
        occurrences.append({'clip_index': index,
                            'sampled_start_frame': context['graphic_start_local_frame'],
                            'sampled_end_frame_exclusive': context['graphic_end_local_frame_exclusive']})
    if not occurrences:
        return {'status': 'unavailable', 'reason': 'No interior graphical occurrence'}
    return {'status': 'experimental', 'needs_manual_review': True,
            'method': 'graphic_context_fallback', 'original_failure': reason,
            'classification': 'unverified_graphic_region', 'occurrences': occurrences,
            'limitations': ['Uniform graphics do not prove separator semantics',
                            'Experimental thresholds; editor alignment still unverified']}


def refine_pair(frames, windows, first, last):
    supports, inside = [], []
    for role in ['departure', 'resume']:
        indices = [index for index, row in enumerate(windows) if row['family_role'] == role]
        features = [frames[index] for index in indices]
        candidates = discover([value[::5] for value in features])
        complete = [row for row in candidates if row['supporting_clips'] == len(indices)]
        refined = (refine(features, complete[0]) if len(complete) == 1 else
                   {'status': 'unavailable', 'reason': 'No unique common motif'})
        if refined.get('status') != 'experimental':
            refined = graphic_family(features, [windows[index] for index in indices], refined['reason'])
        if refined.get('status') != 'experimental':
            raise ValueError(f'Cannot refine {role}: {refined.get("reason", "unknown reason")}')
        supports.append({'family_role': role, 'refinement': refined, 'window_indices': indices})
        for row in refined['occurrences']:
            if row['sampled_start_frame'] <= 0 or row['sampled_end_frame_exclusive'] >= len(features[row['clip_index']]):
                raise ValueError('Insufficient context around a motif; no cut accepted at a window edge')
            index = indices[row['clip_index']]
            origin = windows[index]['first_decoded_frame']
            start, end = origin + row['sampled_start_frame'], origin + row['sampled_end_frame_exclusive']
            if first < start < end <= last:
                inside.append({'family_role': role, 'candidate_index': windows[index]['candidate_index'],
                               'motif_start_decoded_frame': start, 'motif_end_decoded_frame_exclusive': end})
            elif start <= last and end > first:
                raise ValueError('A refined motif crosses an outer bound; review the envelope')
    inside.sort(key=lambda row: row['motif_start_decoded_frame'])
    if not 2 <= len(inside) <= 12 or len(inside) % 2:
        raise ValueError('The internal motifs do not form complete departure/resume pairs')
    previous = first
    for index, row in enumerate(inside):
        expected = 'departure' if index % 2 == 0 else 'resume'
        if row['family_role'] != expected or row['motif_start_decoded_frame'] <= previous:
            raise ValueError('The chosen families do not alternate departure then resume inside the work')
        previous = row['motif_end_decoded_frame_exclusive']
    return {'refinement': {'status': 'experimental', 'roles_explicitly_selected': True, 'needs_manual_review': True,
                           'graphic_fallback_used': any(row['refinement'].get('method') == 'graphic_context_fallback'
                                                        for row in supports)},
            'support_refinements': supports, 'source_motif_limits': inside}
