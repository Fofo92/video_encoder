"""Initial observation windows from an unclassified discovery pool, not cut rules."""
import json
import math
from pathlib import Path
from group_overlay_occurrences import group_sampled_occurrences
from prepare_overlay_review import export_windows


def plan_observations(report,first,last):
    if type(first) is not int or type(last) is not int or not 0<=first<last:
        raise ValueError('Invalid exterior bounds')
    if report.get('status')!='experimental' or report.get('sample_fps')!=5:
        raise ValueError('Expected a five-sample-per-second discovery report')
    candidates=report.get('candidates')
    if not isinstance(candidates,list) or len(candidates)>100:
        raise ValueError('Discovery pool exceeds the bounded observation pilot')
    hits=[]
    for index,candidate in enumerate(candidates,1):
        occurrences=candidate.get('occurrences')
        if not isinstance(occurrences,list) or len(occurrences)>100:
            raise ValueError('Invalid or oversized candidate occurrences')
        for row in occurrences:
            start,end=row.get('core_start_seconds'),row.get('core_end_seconds')
            if (type(start) not in (int,float) or type(end) not in (int,float)
                    or not math.isfinite(start) or not math.isfinite(end) or not 0<=start<end):
                raise ValueError('Invalid discovery occurrence')
            hits.append((start,end,index))
    merged=[]
    for start,end,index in sorted(hits):
        if merged and start<merged[-1]['end_seconds_exclusive']:
            merged[-1]['end_seconds_exclusive']=max(end,merged[-1]['end_seconds_exclusive'])
            merged[-1]['discovery_candidates']=sorted(set(merged[-1]['discovery_candidates']+[index]))
        else:merged.append({'start_seconds':start,'end_seconds_exclusive':end,'discovery_candidates':[index]})
    grouping=group_sampled_occurrences(merged,first/25,(last+1)/25,
                                      coordinate_basis='FFmpeg sampled discovery timeline; source/editor mapping unverified')
    grouping.update(occurrence_origin='unclassified_discovery_pool',
                    discovery_search_partial=bool(report.get('index_limits_reached')))
    groups=[g for g in grouping['groups'] if g['status']=='candidate_temporal_group']
    if not 1<=len(groups)<=3:
        raise ValueError('Les zones repérées ne permettent pas de préparer deux à six extraits sans choix manuel.')
    windows=[]
    for group in groups:
        for row in [group['occurrences'][0],group['occurrences'][-1]]:
            centre=round(row['start_seconds']*25)
            start=max(first,centre-500);end=min(last+1,centre+500)
            windows.append({'name':f'observation-{len(windows)+1}.mp4','first_decoded_frame':start,
                            'end_decoded_frame_exclusive':end,'expected_frame_count':end-start,
                            'planning_basis':'context around unclassified discovery zone endpoint; not a cut'})
    if any(b['first_decoded_frame']<a['end_decoded_frame_exclusive'] for a,b in zip(windows,windows[1:])):
        raise ValueError('Les extraits proposés se chevauchent ; les zones restent à examiner.')
    return grouping,windows


def export_observations(report_path,source,bounds,output):
    encoded=report_path.read_bytes();report=json.loads(encoded)
    if source.resolve()!=Path(report['source']).resolve():
        raise ValueError('Discovery report concerns another recording')
    grouping,windows=plan_observations(report,*bounds)
    export_windows(report_path,encoded,grouping,windows,output,observation_bounds=bounds)
    return output/'frame-map.json'
