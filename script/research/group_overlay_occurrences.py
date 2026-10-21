"""Bounded temporal grouping of graphic occurrences, not advertisement decisions.

Only programme exterior times and a presence-scan report are inputs. No reviewed
interior cuts are accepted. Local adjacency can still merge unrelated graphics.
"""
import argparse
import json
import math
from pathlib import Path


def group_occurrences(report, programme_start, programme_end, max_gap=300., max_span=600., min_span=60.):
    settings=[programme_start,programme_end,max_gap,max_span,min_span]
    if (any(type(value) not in [int,float] or not math.isfinite(value) for value in settings)
            or not 0 <= programme_start < programme_end or not 0 < max_gap <= max_span <= 1200
            or not 0 < min_span < max_span):
        raise ValueError('Invalid programme times or grouping bounds')
    if report.get('status')!='completed' or report.get('sample_fps')!=5:
        raise ValueError('Expected a completed five-sample-per-second presence scan')
    rows=report.get('occurrences')
    if not isinstance(rows,list) or len(rows)>10000:
        raise ValueError('Expected at most 10000 graphic occurrences')
    previous=-1;inside=[];outside=[];boundary=[]
    for row in rows:
        start,end=row.get('start_seconds'),row.get('end_seconds_exclusive')
        if (type(start) not in [int,float] or type(end) not in [int,float]
                or not math.isfinite(start) or not math.isfinite(end) or not 0<=start<end
                or start<previous):
            raise ValueError('Graphic occurrences must be finite, ordered and disjoint')
        previous=end
        if end<=programme_start or start>=programme_end:
            outside.append(row)
        elif start<programme_start or end>programme_end:
            boundary.append(row)
        else:inside.append(row)
    clusters=[]
    for row in inside:
        if not clusters or row['start_seconds']-clusters[-1][-1]['end_seconds_exclusive']>max_gap:
            clusters.append([])
        clusters[-1].append(row)
    groups=[]
    for cluster in clusters:
        span=cluster[-1]['end_seconds_exclusive']-cluster[0]['start_seconds']
        if len(cluster)<2:status='isolated_graphic'
        elif span>max_span:status='ambiguous_overlong_cluster'
        elif span<min_span:status='short_cluster'
        else:status='candidate_temporal_group'
        groups.append({'status':status,'needs_manual_review':True,'occurrences':cluster,
                       'graphic_span_seconds':span,'first_graphic_seconds':cluster[0]['start_seconds'],
                       'last_graphic_end_seconds_exclusive':cluster[-1]['end_seconds_exclusive'],
                       'interior_graphic_count':max(0,len(cluster)-2)})
    return {'status':'experimental_temporal_grouping','needs_manual_review':True,
            'programme_bounds_seconds':[programme_start,programme_end],
            'settings':{'max_gap_seconds':max_gap,'max_span_seconds':max_span,'min_span_seconds':min_span},
            'inside_occurrence_count':len(inside),'outside_occurrence_count':len(outside),
            'straddling_occurrences':boundary,'groups':groups,
            'coordinate_basis':report.get('coordinate_basis'),
            'limitations':['Exterior programme times must use a compatible timeline',
                           'Temporal grouping does not prove that all intervening content is advertising',
                           'Isolated or ambiguous graphics do not prove absence of an advertisement break',
                           'Interior graphic occurrences are retained, not silently deleted',
                           'No expected number of breaks or reviewed interior cut positions are inputs',
                           'No source-frame conversion, cut decisions or montage']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True)
    parser.add_argument('--programme-start',type=float,required=True)
    parser.add_argument('--programme-end',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=group_occurrences(json.loads(args.report.read_text()),args.programme_start,args.programme_end)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
