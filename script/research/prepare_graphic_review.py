"""One research run from source, observations and exterior bounds to raccord review.

Both graphic hypotheses are tried without a channel or detector choice. This is
observation-assisted research, not blind discovery and never an accepted montage.
"""
import argparse
import json
from pathlib import Path
import time
from scan_stable_overlays import run as scan
from group_overlay_occurrences import group_occurrences
from prepare_overlay_review import export, plan, verify_native_rate
from refine_overlay_review import refine


def write_json(path,value):
    pending=path.with_suffix('.pending')
    pending.write_text(json.dumps(value,indent=2)+'\n')
    pending.replace(path)


def run(source,observations,in_frame,out_frame,output):
    if type(in_frame) is not int or type(out_frame) is not int or not 0<=in_frame<out_frame:
        raise ValueError('Expected ordered exterior frame indices; OUT is inclusive')
    start,end=in_frame/25,(out_frame+1)/25
    source=source.resolve(strict=True)
    output=output.resolve()
    verify_native_rate(source)
    output.mkdir(parents=True,exist_ok=False)
    report_path=output/'pipeline.json';started=time.monotonic()
    report={'status':'running','stage':'scanning','source':str(source),'needs_manual_review':True,
            'exterior_bounds_frames_inclusive':[in_frame,out_frame],
            'programme_bounds_seconds':[start,end],'edge_modes_requested':['white','contrast'],
            'source_editor_mapping_verified':False,'reviewed_interior_cuts_used':False,
            'limitations':['Selected observations are required; this is not blind source-only discovery',
                           'Merged graphic signals do not establish advertisement semantics',
                           'No montage, project, source modification or encoding queue changes']}
    def save():
        report['elapsed_seconds']=round(time.monotonic()-started)
        write_json(report_path,report)
    def stage(name):
        report['stage']=name;save()
        print(f'Review preparation: {name}; elapsed {report["elapsed_seconds"]} s',flush=True)
    save()
    try:
        scan_path=scan(source,observations,output/'scan',edge_mode='both')
        report['scan_report']=str(scan_path)
        stage('grouping')
        presence=json.loads(scan_path.read_text())
        grouping=group_occurrences(presence,start,end)
        write_json(output/'groups.json',grouping)
        report['grouping_report']=str(output/'groups.json')
        candidate_groups=[g for g in grouping['groups'] if g['status']=='candidate_temporal_group']
        report['candidate_group_count']=len(candidate_groups)
        report['unresolved_group_count']=len(grouping['groups'])-len(candidate_groups)
        report['straddling_occurrence_count']=len(grouping['straddling_occurrences'])
        try:plan(presence,start,end)
        except ValueError as error:
            report.update(status='needs_review',stage='grouping',reason=str(error));save()
            return report_path
        report['review_directory']=str(output/'raccords')
        stage('extracting')
        export(scan_path,start,end,output/'raccords')
        report['review_manifest']=str(output/'raccords/frame-map.json')
        stage('refining')
        result=refine(output/'raccords')
        write_json(output/'raccords.json',result)
        report['raccord_report']=str(output/'raccords.json')
        resolved=(result['status']=='candidate_raccords' and report['unresolved_group_count']==0
                  and report['straddling_occurrence_count']==0)
        report.update(status='ready_for_review' if resolved else 'needs_review',stage='completed',
                      candidate_raccord_count=sum(r['status']=='candidate_raccord' for r in result['raccords']))
        save()
        return report_path
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                      error=f'{type(error).__name__}: {error}')
        save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--clips',type=Path,nargs='+',required=True)
    parser.add_argument('--in-frame',type=int,required=True)
    parser.add_argument('--out-frame',type=int,required=True,help='Inclusive exterior OUT at 25 fps')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(run(args.source,args.clips,args.in_frame,args.out_frame,args.output))
