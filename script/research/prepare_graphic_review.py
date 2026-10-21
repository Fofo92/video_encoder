"""One research run from source, exterior bounds and discovery or observations.

Both graphic hypotheses are tried without a channel or detector choice. This is
experimental evidence preparation; proposals never become an accepted montage automatically.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
from scan_stable_overlays import run as scan
from group_overlay_occurrences import group_occurrences
from prepare_overlay_review import export, export_windows, plan, verify_native_rate
from refine_overlay_review import refine
from export_indexed_windows import source_identity
from graphic_observation_manifest import observations_from_manifest
from bootstrap_graphic_observations import export_observations,plan_observations
from graphic_review_cache import completed_scan,completed_review,completed_export,copy_scan,copy_review
from format_break_hypotheses import cached_format_review


def write_json(path,value):
    pending=path.with_suffix('.pending')
    pending.write_text(json.dumps(value,indent=2)+'\n')
    pending.replace(path)


def run(source,observations,in_frame,out_frame,output,observation_manifest=None,discovery_report=None,cache_root=None):
    if type(in_frame) is not int or type(out_frame) is not int or not 0<=in_frame<out_frame:
        raise ValueError('Expected ordered exterior frame indices; OUT is inclusive')
    start,end=in_frame/25,(out_frame+1)/25
    source=source.resolve(strict=True)
    if sum([bool(observations),observation_manifest is not None,discovery_report is not None])>1:
        raise ValueError('Use one observation input route')
    output=output.resolve()
    cache_root=Path(cache_root) if cache_root is not None else Path(__file__).resolve().parents[2]/'tmp'
    verify_native_rate(source)
    output.mkdir(parents=True,exist_ok=False)
    report_path=output/'pipeline.json';started=time.monotonic()
    report={'status':'running','stage':'scanning','source':str(source),'needs_manual_review':True,
            'source_identity':source_identity(source),
            'exterior_bounds_frames_inclusive':[in_frame,out_frame],
            'programme_bounds_seconds':[start,end],'edge_modes_requested':['white','contrast'],
            'source_editor_mapping_verified':False,'reviewed_interior_cuts_used':False,
            'observation_selection':'automatic_discovery_context' if discovery_report is not None else 'provided_observations',
            'limitations':['Observation windows contain proposals, not verified advertising separators',
                           'Merged graphic signals do not establish advertisement semantics',
                           'No montage, project, source modification or encoding queue changes']}
    def save():
        report['elapsed_seconds']=round(time.monotonic()-started)
        write_json(report_path,report)
    def stage(name):
        report['stage']=name;save()
        print(f'Review preparation: {name}; elapsed {report["elapsed_seconds"]} s',flush=True)
        format_method=report.get('preparation_method')=='format_hypotheses'
        steps={'scanning':(1,'Analyse rapide du cache de cadrage' if format_method else 'Analyse graphique de l’enregistrement'),
               'grouping':(2,'Repérage des changements de cadrage' if format_method else 'Regroupement des repères graphiques'),
               'extracting':(3,'Extraction des raccords à contrôler'),
               'refining':(4,'Préparation des images de raccord')}
        if name=='observing':step,label=1,'Préparation des extraits d’observation'
        else:
            step,label=steps[name]
            if discovery_report is not None and not format_method:step+=1
        print('REVIEW_STAGE '+json.dumps({'step':step,'total':5 if discovery_report is not None and not format_method else 4,'label':label}),flush=True)
    save()
    try:
        try:
            format_result=cached_format_review(source,cache_root,in_frame,out_frame)
        except (OSError,ValueError,KeyError,TypeError) as error:
            format_result={'status':'unavailable','reason':str(error)}
        write_json(output/'format-check.json',format_result)
        report['format_preflight_status']=format_result['status']
        if format_result['status']=='candidate_format_windows':
            report.update(preparation_method='format_hypotheses',recording_scan_started=False,
                          observation_selection='not_used_for_format_review',limitations=format_result['limitations'])
            stage('scanning');stage('grouping')
            grouping={key:value for key,value in format_result.items() if key!='windows'}
            write_json(output/'groups.json',grouping)
            report.update(grouping_report=str(output/'groups.json'),
                          candidate_group_count=len(format_result['groups']),unresolved_group_count=0,
                          straddling_occurrence_count=0,review_directory=str(output/'raccords'))
            stage('extracting')
            format_path=output/'format-check.json'
            previous=completed_export(cache_root,source,format_path,grouping,format_result['windows'])
            if previous is not None:
                copy_review(previous,output/'raccords')
                report['reused_review_from']=str(previous)
            else:
                export_windows(format_path,format_path.read_bytes(),grouping,format_result['windows'],output/'raccords')
            report['review_manifest']=str(output/'raccords/frame-map.json')
            stage('refining')
            result=refine(output/'raccords')
            if source_identity(source)!=report['source_identity']:
                raise ValueError('Recording changed during format review')
            result.update(outer_bounds=[in_frame,out_frame],review_origin='format_hypotheses')
            write_json(output/'raccords.json',result)
            report.update(raccord_report=str(output/'raccords.json'),stage='completed',
                          candidate_raccord_count=sum(r['status']=='candidate_raccord' for r in result['raccords']),
                          status='ready_for_review' if result['status']=='candidate_raccords' else 'needs_review')
            save()
            return report_path
        if discovery_report is not None:
            discovery_report=discovery_report.resolve(strict=True)
            stage('observing')
            discovery=json.loads(discovery_report.read_text())
            if (Path(discovery['source']).resolve()!=source
                    or discovery.get('source_identity')!=report['source_identity']):
                raise ValueError('Discovery report does not match the unchanged recording')
            report.update(discovery_report=str(discovery_report),
                          discovery_search_partial=bool(discovery.get('index_limits_reached')))
            try:plan_observations(discovery,in_frame,out_frame)
            except ValueError as error:
                report.update(status='needs_review',reason=str(error));save()
                return report_path
            observation_manifest=export_observations(discovery_report,source,(in_frame,out_frame),output/'observations')
        stage('scanning')
        if observation_manifest is not None:
            observation_manifest=observation_manifest.resolve(strict=True)
            observations,digest=observations_from_manifest(observation_manifest,source,(in_frame,out_frame))
            report.update(observation_manifest=str(observation_manifest),observation_manifest_sha256=digest)
            save()
        previous=completed_scan(cache_root,source,observations) if observations else None
        if previous is not None:
            scan_path=copy_scan(previous,output/'scan')
            report['reused_scan_from']=str(previous)
            print('Réutilisation du scan terminé : aucune nouvelle lecture complète pour cette étape.',flush=True)
        else:
            scan_path=scan(source,observations,output/'scan',edge_mode='both')
        if (observation_manifest is not None and hashlib.sha256(observation_manifest.read_bytes()).hexdigest()
                !=report['observation_manifest_sha256']):
            raise ValueError('Observation extraction manifest changed during the scan')
        report['scan_report']=str(scan_path)
        stage('grouping')
        presence=json.loads(scan_path.read_text())
        if presence.get('source_identity')!=report['source_identity']:
            raise ValueError('Recording changed between preparation and scanning')
        if presence.get('status')=='needs_review':
            report.update(status='needs_review',stage='completed',candidate_raccord_count=0,
                          reason=presence['reason'],recording_scan_started=False,
                          learning_abstention=presence.get('learning_abstention'))
            save()
            return report_path
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
        previous=completed_review(cache_root,source,scan_path,in_frame,out_frame)
        if previous is not None:
            copy_review(previous,output/'raccords')
            report['reused_review_from']=str(previous)
            print('Réutilisation des extraits natifs vérifiés.',flush=True)
        else:
            export(scan_path,start,end,output/'raccords')
        report['review_manifest']=str(output/'raccords/frame-map.json')
        stage('refining')
        result=refine(output/'raccords')
        if source_identity(source)!=report['source_identity']:
            raise ValueError('Recording changed during raccord preparation')
        result.update(outer_bounds=[in_frame,out_frame],review_origin='graphic_hypotheses')
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
    observations=parser.add_mutually_exclusive_group(required=True)
    observations.add_argument('--clips',type=Path,nargs='+')
    observations.add_argument('--observation-manifest',type=Path)
    observations.add_argument('--discovery-report',type=Path)
    parser.add_argument('--in-frame',type=int,required=True)
    parser.add_argument('--out-frame',type=int,required=True,help='Inclusive exterior OUT at 25 fps')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    print(run(args.source,args.clips or [],args.in_frame,args.out_frame,args.output,args.observation_manifest,args.discovery_report))
