"""Reuse complete research steps only for the same source, observations and plan."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from export_indexed_windows import source_identity
from prepare_overlay_review import plan
from stable_overlay_signals import GRAPHIC_ALGORITHM_REVISION


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def newest(root,pattern):
    def modified(path):
        try:return path.stat().st_mtime_ns
        except OSError:return -1
    return sorted(Path(root).glob(pattern),key=modified,reverse=True)


def completed_scan(root,source,observations):
    if not 2<=len(observations)<=6:return None
    source=source.resolve(strict=True);current=source_identity(source)
    expected=[]
    for path in observations:
        path=path.resolve(strict=True);before=source_identity(path);sha=digest(path)
        if source_identity(path)!=before:raise ValueError('Observation changed while checking cached results')
        expected.append({'path':str(path),'identity':before,'sha256':sha})
    expected.sort(key=lambda row:row['path'])
    for path in newest(root,'**/report.json'):
        try:
            report=json.loads(path.read_text())
            if not isinstance(report,dict):continue
            if (report.get('status')!='completed' or report.get('source')!=str(source)
                    or report.get('source_identity')!=current or report.get('edge_mode')!='both'
                    or report.get('sample_fps')!=5 or report.get('threshold')!=.8
                    or report.get('minimum_samples')!=3):continue
            # Known pre-cache reports used the same v1 scoring and persisted settings.
            if report.get('algorithm_revision','shared-graphic-v1')!=GRAPHIC_ALGORITHM_REVISION:continue
            if sorted(report.get('observations',[]),key=lambda row:row['path'])!=expected:continue
            models=report.get('learned_graphics',[])
            if not isinstance(models,list) or not 1<=len(models)<=2 or any(not isinstance(m,dict) or m.get('source_shape')!=[360,640]
                    or m.get('edge_mode') not in ('white','contrast')
                    or m.get('selection')!='largest_shared_edge_region; unclassified graphic' for m in models):continue
            modes={m['edge_mode'] for m in models}
            if len(modes)!=len(models) or set(report.get('occurrences_by_hypothesis',{}))!=modes:continue
            if set(report.get('hypothesis_abstentions',{}))!={'white','contrast'}-modes:continue
            if type(report.get('sampled_frames')) is not int or not 0<report['sampled_frames']<=108000:continue
            from group_overlay_occurrences import group_occurrences
            group_occurrences(report,0,report['sampled_frames']/5)
            return path
        except (OSError,ValueError,KeyError,TypeError,AttributeError):continue
    return None


def completed_review(root,source,scan_path,first,last):
    encoded=scan_path.read_bytes();report=json.loads(encoded)
    grouping,windows=plan(report,first/25,(last+1)/25)
    return completed_export(root,source,scan_path,grouping,windows)


def completed_export(root,source,scan_path,grouping,windows):
    encoded=scan_path.read_bytes()
    current=source_identity(source);sha=hashlib.sha256(encoded).hexdigest()
    for path in newest(root,'**/frame-map.json'):
        try:
            data=json.loads(path.read_text())
            if not isinstance(data,dict):continue
            if (data.get('status')!='export_complete_editor_alignment_unverified' or data.get('fps')!=25
                    or data.get('source')!=str(source.resolve()) or data.get('source_identity')!=current
                    or data.get('presence_report_sha256')!=sha or data.get('groups')!=grouping):continue
            actual=data.get('windows',[])
            if len(actual)!=len(windows):continue
            valid=True
            for row,expected in zip(actual,windows):
                if {key:value for key,value in row.items() if key!='sha256'}!=expected:
                    valid=False;break
                name=row['name'];clip=(path.parent/name).resolve(strict=True)
                if Path(name).name!=name or clip.parent!=path.parent.resolve() or digest(clip)!=row.get('sha256'):
                    valid=False;break
            if valid:return path.parent
        except (OSError,ValueError,KeyError,TypeError,AttributeError):continue
    return None


def copy_scan(previous,output):
    encoded=previous.read_bytes();output.mkdir(parents=True,exist_ok=False)
    (output/'report.json').write_bytes(encoded)
    for name in ['learned-overlay-white.npz','learned-overlay-contrast.npz']:
        model=previous.parent/name
        if model.is_file():shutil.copyfile(model,output/name)
    if previous.read_bytes()!=encoded:raise ValueError('Cached scan changed during reuse')
    return output/'report.json'


def copy_review(previous,output):
    path=previous/'frame-map.json';encoded=path.read_bytes();data=json.loads(encoded)
    output.mkdir(parents=True,exist_ok=False)
    (output/'frame-map.json').write_bytes(encoded)
    for row in data['windows']:
        shutil.copyfile(previous/row['name'],output/row['name'])
        if digest(output/row['name'])!=row['sha256']:raise ValueError('Cached clip changed during reuse')
    if path.read_bytes()!=encoded:raise ValueError('Cached frame map changed during reuse')
    with Path(str(output)+'.tar.gz').open('xb') as stream:
        with tarfile.open(fileobj=stream,mode='w:gz') as archive:archive.add(output,arcname=output.name)
