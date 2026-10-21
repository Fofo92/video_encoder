"""Observation-assisted review adapters; proposed raccords stay unconfirmed."""
import hashlib
import json
from pathlib import Path
from .repeated_sequence_review import identity
from .trim_session import TrimSession, SourceReference, SegmentSelection


def observation_manifest(repository,source,bounds):
    """Locate available observation pixels, not a chosen detector or cut rule.

    Only cheap metadata checks run here. The child worker verifies clip counts,
    timing, checksums and the manifest again before learning.
    """
    source=Path(source).resolve()
    try:current=identity(source)
    except OSError:return None
    root=Path(repository)/'tmp/repeated-sequence-reviews'
    paths=sorted([*root.glob('*/manifest.json'),*root.glob('*/observations/frame-map.json')],
                 key=lambda path:path.stat().st_mtime_ns,reverse=True)
    for path in paths:
        try:
            data=json.loads(path.read_text())
            if Path(data['source']).resolve()!=source or data.get('source_identity')!=current:
                continue
            windows=data.get('windows',[])
            if not isinstance(windows,list) or len(windows)>24:continue
            clips=[]
            for window in windows:
                first,last=window.get('first_decoded_frame'),window.get('end_decoded_frame_exclusive')
                if type(first) is not int or type(last) is not int or not 0<=first<last:
                    raise ValueError('Invalid observation range')
                if first<bounds[0] or last>bounds[1]+1:continue
                name=window['name']
                if not isinstance(name,str) or Path(name).name!=name:raise ValueError('Invalid clip name')
                clip=(path.parent/name).resolve()
                if clip.parent!=path.parent.resolve() or not clip.is_file() or not 25<=last-first<=1500:
                    raise ValueError('Invalid clip path or duration')
                clips.append(clip)
            if 2<=len(clips)<=6 and len(set(clips))==len(clips):return path
        except (OSError,ValueError,KeyError,TypeError):continue
    return None


def check_graphic_source(report,source,first,last):
    if (report.get('review_origin') not in ('graphic_hypotheses','format_hypotheses') or report.get('fps')!=25
            or Path(report['source']).resolve()!=Path(source).resolve()
            or report.get('source_identity')!=identity(source) or report.get('outer_bounds')!=[first,last]):
        raise ValueError('La revue graphique ne correspond pas à la source inchangée et à ses bornes extérieures.')


def graphic_preview_rows(report,first,last):
    rows=report.get('raccords')
    if not isinstance(rows,list) or len(rows)>12 or len(rows)%2:
        raise ValueError('Paires de raccords graphiques invalides.')
    preview=[]
    for index,row in enumerate(rows):
        role='departure' if index%2==0 else 'resume'
        if row.get('candidate_role')!=role or row.get('group_index')!=index//2+1:
            raise ValueError('Les raccords ne forment pas une alternance départ/reprise.')
        if row.get('status')!='candidate_raccord':continue
        kept,transition=row.get('candidate_kept_decoded_frame'),row.get('candidate_transition_decoded_frame')
        meaning='last_kept' if role=='departure' else 'first_kept'
        if (type(kept) is not int or type(transition) is not int or not first<kept<last
                or kept!=(transition-1 if role=='departure' else transition) or row.get('kept_frame_meaning')!=meaning):
            raise ValueError('Convention ou indice de raccord graphique invalide.')
        preview.append({'start':transition,'end':transition+1,'candidate_role':role,'group_index':index//2+1,
                        'report_index':index,'kept_frame':kept,'excluded_frame':transition if role=='departure' else transition-1})
    return preview


def proposed_graphic_session(report,source,first,last,confirmed=False):
    check_graphic_source(report,source,first,last)
    if not confirmed:raise ValueError('Confirme les raccords avant de charger les segments.')
    rows=graphic_preview_rows(report,first,last)
    if report.get('status')!='candidate_raccords' or not 2<=len(rows)<=12 or len(rows)!=len(report['raccords']):
        raise ValueError('Des raccords graphiques restent à examiner ; aucun montage complet ne peut être chargé.')
    session=TrimSession();session.add_source(SourceReference('source',Path(source)))
    beginning=first
    for departure,resume in zip(rows[::2],rows[1::2]):
        end,start=departure['kept_frame'],resume['kept_frame']
        if not beginning<end or not end+1<start:
            raise ValueError('Les segments proposés sont vides ou se chevauchent.')
        session.add_segment(SegmentSelection('source',beginning,end));beginning=start
    session.add_segment(SegmentSelection('source',beginning,last))
    return session


def load_graphic_review(path,source,bounds):
    path=Path(path);pipeline=json.loads(path.read_text())
    if (pipeline.get('status') not in ('ready_for_review','needs_review')
            or Path(pipeline['source']).resolve()!=Path(source).resolve()
            or pipeline.get('source_identity')!=identity(source)
            or pipeline.get('exterior_bounds_frames_inclusive')!=list(bounds)):
        raise ValueError('La préparation graphique est incomplète, périmée ou concerne une autre source.')
    report_path=path.parent/'raccords.json'
    if not report_path.is_file():
        if pipeline['status']=='ready_for_review':raise ValueError('Le rapport des raccords est absent.')
        return pipeline,None
    report=json.loads(report_path.read_text())
    check_graphic_source(report,source,*bounds)
    manifest=path.parent/'raccords/frame-map.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest()!=report.get('review_manifest_sha256'):
        raise ValueError('Le manifeste des raccords a changé depuis leur préparation.')
    graphic_preview_rows(report,*bounds)
    if pipeline['status']=='ready_for_review':proposed_graphic_session(report,source,*bounds,confirmed=True)
    return pipeline,report
