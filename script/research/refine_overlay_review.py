"""Candidate raccords from decoded-index review clips; no montage or acceptance.

Reference cuts are not inputs. Source/editor mapping still requires review.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import numpy as np
from jingle_boundary_signals import boundary_evidence
from letterbox_signals import classify_frames, summarize


def digest(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):result.update(block)
    return result.hexdigest()


def refine_window(frames,window,occurrence):
    role=window['candidate_role'];first=window['first_decoded_frame']
    anchor=window['approximate_graphic_local_frame']
    if role not in ['departure','resume'] or type(first) is not int or first<0 or type(anchor) is not int:
        raise ValueError('Invalid review role or decoded index')
    duration=occurrence['end_seconds_exclusive']-occurrence['start_seconds']
    if not math.isfinite(duration) or duration<=0:
        raise ValueError('Invalid graphic duration')
    end=anchor+max(1,round(duration*25))
    evidence=boundary_evidence(frames,(anchor,end),fps=25.)
    candidates=evidence['opening_candidates' if role=='departure' else 'closing_candidates']
    ranked=[{**row,'decoded_transition_frame':first+row['observation_frame']} for row in candidates]
    result={'candidate_role':role,'group_index':window['group_index'],'needs_manual_review':True,
            'candidates':ranked,'status':'unresolved_no_transition'}
    if not candidates:return result
    ratio=(candidates[0]['pixel_change']/candidates[1]['pixel_change'] if len(candidates)>1 else None)
    result['strongest_to_runner_up_ratio']=ratio
    if candidates[0]['kind']=='enter_black':
        result['status']='ambiguous_black_entry';return result
    if ratio is not None and ratio<1.5:
        result['status']='ambiguous_competing_transitions';return result
    transition=ranked[0]['decoded_transition_frame']
    result.update(status='candidate_raccord',candidate_transition_decoded_frame=transition,
                  candidate_kept_decoded_frame=transition-1 if role=='departure' else transition,
                  kept_frame_meaning='last_kept' if role=='departure' else 'first_kept')
    return result


def refine_format_window(frames,window):
    role=window['candidate_role'];first=window['first_decoded_frame']
    expected=('letterboxed','full_frame') if role=='departure' else ('full_frame','letterboxed')
    bracket=window['format_transition_bracket_seconds']
    centre=sum(bracket)/2-first/25
    evidence=summarize(classify_frames(frames),sample_fps=25,stable_seconds=.4,max_unknown_gap_seconds=2)
    changes=[row for row in evidence['format_changes'] if (row['from'],row['to'])==expected
             and abs(sum(row['time_bracket_seconds'])/2-centre)<=4]
    result={'candidate_role':role,'group_index':window['group_index'],'needs_manual_review':True,
            'status':'unresolved_no_format_transition','candidates':[],
            'format_changes':changes,'evidence_method':'native_bilateral_band_transition'}
    if len(changes)!=1:
        if changes:result['status']='ambiguous_competing_format_transitions'
        return result
    left,right=changes[0]['time_bracket_seconds']
    lo=max(1,round(left*25)+1);hi=min(len(frames)-1,round(right*25))
    differences=np.mean(np.abs(frames[1:].astype(np.float32)-frames[:-1]),axis=(1,2,3))
    ranked=[]
    for at in sorted(range(lo,hi+1),key=lambda at:float(differences[at-1]),reverse=True):
        if float(differences[at-1])<20:continue
        if any(abs(at-row['observation_frame'])<8 for row in ranked):continue
        ranked.append({'observation_frame':at,'seconds':at/25,'pixel_change':float(differences[at-1]),
                       'kind':'format_context_visual_change','decoded_transition_frame':first+at})
        if len(ranked)==5:break
    result['candidates']=ranked
    if not ranked:return result
    ratio=ranked[0]['pixel_change']/ranked[1]['pixel_change'] if len(ranked)>1 else None
    result['strongest_to_runner_up_ratio']=ratio
    if ratio is not None and ratio<1.5:
        result['status']='ambiguous_competing_transitions';return result
    transition=ranked[0]['decoded_transition_frame']
    result.update(status='candidate_raccord',candidate_transition_decoded_frame=transition,
                  candidate_kept_decoded_frame=transition-1 if role=='departure' else transition,
                  kept_frame_meaning='last_kept' if role=='departure' else 'first_kept')
    return result


def refine(directory):
    directory=directory.resolve(strict=True)
    manifest_path=directory/'frame-map.json';encoded=manifest_path.read_bytes();manifest=json.loads(encoded)
    if manifest.get('status')!='export_complete_editor_alignment_unverified' or manifest.get('fps')!=25:
        raise ValueError('Expected a complete 25 fps decoded-index review export')
    groups=[g for g in manifest['groups']['groups'] if g['status'] in ('candidate_temporal_group','candidate_format_group')]
    windows=manifest['windows']
    if not 1<=len(groups)<=6 or len(windows)!=2*len(groups):
        raise ValueError('Expected paired review windows for each candidate group')
    results=[];previous=-1;seen=set()
    for index,window in enumerate(windows):
        role='departure' if index%2==0 else 'resume';group_number=index//2+1
        if window['candidate_role']!=role or window['group_index']!=group_number:
            raise ValueError('Review windows are not ordered candidate pairs')
        name=window['name']
        if Path(name).name!=name or name in seen:
            raise ValueError('Expected distinct local review clip names')
        seen.add(name);path=(directory/name).resolve(strict=True)
        if path.parent!=directory or digest(path)!=window.get('sha256'):
            raise ValueError('Review clip path or checksum differs')
        first,last=window['first_decoded_frame'],window['end_decoded_frame_exclusive']
        count=window['expected_frame_count']
        if (type(first) is not int or type(last) is not int or type(count) is not int
                or first<previous or last-first!=count or not 2<=count<=600):
            raise ValueError('Invalid, overlapping or oversized decoded review interval')
        previous=last
        raw=subprocess.check_output(['ffmpeg','-v','error','-nostdin','-i',str(path),'-map','0:v:0',
                                     '-an','-sn','-dn','-vf','scale=160:90','-frames:v',str(count+1),
                                     '-pix_fmt','rgb24','-fps_mode','passthrough','-f','rawvideo','pipe:1'])
        if len(raw)!=count*160*90*3:
            raise ValueError('Decoded review length differs from its frame map')
        frames=np.frombuffer(raw,dtype=np.uint8).reshape(count,90,160,3)
        group=groups[group_number-1]
        if group['status']=='candidate_format_group':
            results.append(refine_format_window(frames,window))
        else:
            occurrence=group['occurrences'][0 if role=='departure' else -1]
            results.append(refine_window(frames,window,occurrence))
        if digest(path)!=window['sha256']:
            raise ValueError('Review clip changed during refinement')
    if manifest_path.read_bytes()!=encoded:
        raise ValueError('Review manifest changed during refinement')
    return {'status':'candidate_raccords' if all(r['status']=='candidate_raccord' for r in results) else 'unresolved_raccords',
            'needs_manual_review':True,'source':manifest['source'],'source_identity':manifest['source_identity'],
            'review_manifest_sha256':hashlib.sha256(encoded).hexdigest(),'fps':25,'raccords':results,
            'original_recording_accessed':False,'source_editor_mapping_verified':False,
            'limitations':['Graphic grouping and strongest transition do not prove advertisement semantics',
                           'Candidate kept frames use decoded source indices, not verified editor coordinates',
                           'No reference cuts, montage, project writes or encoding queue changes']}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Output already exists')
    result=refine(args.review)
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(args.output)
