"""Conditional format excursions from sealed cached pixels, never accepted cuts."""
import hashlib
import json
from pathlib import Path
import numpy as np
from audit_capture_signals import latest_cache
from discover_source_sequences import load_cache
from export_indexed_windows import source_identity
from letterbox_signals import classify_frames


def runs(values):
    starts=np.r_[0,np.flatnonzero(values[1:]!=values[:-1])+1]
    return [(int(a),int(b),bool(values[a]))
            for a,b in zip(starts,np.r_[starts[1:],len(values)])]


def plan_format_review(labels, first, last):
    labels=np.asarray(labels)
    if (labels.ndim!=1 or not np.isin(labels,[-1,0,1]).all()
            or type(first) is not int or type(last) is not int or not 0<=first<last
            or last//5>=len(labels)):
        raise ValueError('Invalid five-Hz labels or 25-fps exterior bounds')
    offset=(first+4)//5
    labels=labels[offset:last//5+1]
    report={'status':'needs_review','needs_manual_review':True,'method':'conditional_bilateral_bands_v1',
            'sample_fps':5,'programme_bounds_seconds':[first/25,(last+1)/25],
            'groups':[],'unresolved_groups':[],'windows':[],
            'settings':{'minimum_known_fraction':.5,'minimum_letterbox_fraction_of_known':.75,
                        'occupancy_window_seconds':5,'minimum_known_samples_per_window':10,
                        'minimum_local_letterbox_fraction':.8,'bridge_seconds':5,
                        'minimum_anchor_seconds':120,'minimum_full_frame_seconds':30,
                        'maximum_excursion_seconds':900},
            'reviewed_interior_cuts_used':False,'source_editor_mapping_verified':False,
            'limitations':['A change of framing is not proof of advertising',
                           'Brief or letterboxed advertisements may be missed',
                           'No expected break count, channel template or reference cuts are inputs',
                           'Sampled brackets require native extraction and human review']}
    known=int(np.sum(labels!=-1));boxed=int(np.sum(labels==1))
    report['state_counts']={'unknown':int(np.sum(labels==-1)),'full_frame':int(np.sum(labels==0)),
                            'letterboxed':boxed}
    if len(labels)<25 or known<.5*len(labels) or boxed<.75*known:
        report['reason']='Les bandes noires ne constituent pas un repère dominant assez stable.'
        return report
    kernel=np.ones(25,dtype=int)
    known_near=np.convolve((labels!=-1).astype(int),kernel,'same')
    boxed_near=np.convolve((labels==1).astype(int),kernel,'same')
    support=(known_near>=10)&(boxed_near>=.8*known_near)
    for a,b,state in runs(support):
        if not state and b-a<=25 and a>0 and b<len(support):support[a:b]=True
    anchors=[(a,b) for a,b,state in runs(support) if state and b-a>=600]
    report['anchors_seconds']=[[(offset+a)/5,(offset+b)/5] for a,b in anchors]
    for before,after in zip(anchors,anchors[1:]):
        a,b=before[1],after[0];part=labels[a:b];full=np.flatnonzero(part==0)
        if len(full)<150:continue  # Darkness alone is not positive full-frame evidence.
        if b-a>4500 or len(full)<.5*np.sum(part!=-1):
            report['unresolved_groups'].append({'start_seconds':(offset+a)/5,
                'end_seconds_exclusive':(offset+b)/5,'reason':'Mixed or overlong format excursion'})
            continue
        start=a+int(full[0]);end=a+int(full[-1])
        preceding=np.flatnonzero(labels[before[0]:start]==1)
        following=np.flatnonzero(labels[end+1:after[1]]==1)
        if not len(preceding) or not len(following):continue
        brackets=[[(offset+before[0]+int(preceding[-1]))/5,(offset+start)/5],
                  [(offset+end)/5,(offset+end+1+int(following[0]))/5]]
        number=len(report['groups'])+1;windows=[]
        for role,bracket in zip(['departure','resume'],brackets):
            lo=max(first,round(bracket[0]*25)-150)
            hi=min(last+1,round(bracket[1]*25)+151)
            windows.append({'name':f'{role}-{number}.mp4','candidate_role':role,'group_index':number,
                            'first_decoded_frame':lo,'end_decoded_frame_exclusive':hi,
                            'expected_frame_count':hi-lo,'format_transition_bracket_seconds':bracket,
                            'centre_planning_basis':'sampled bilateral-band transition; not a cut'})
        if any(not 2<=w['expected_frame_count']<=600 for w in windows):
            report['unresolved_groups'].append({'reason':'Format transition bracket too wide','brackets':brackets})
            continue
        report['groups'].append({'status':'candidate_format_group','needs_manual_review':True,
                                  'transition_brackets_seconds':brackets,'full_frame_seconds':len(full)/5})
        report['windows'].extend(windows)
    if (not 1<=len(report['groups'])<=6 or report['unresolved_groups']
            or any(a['end_decoded_frame_exclusive']>b['first_decoded_frame']
                   for a,b in zip(report['windows'],report['windows'][1:]))):
        report['reason']='Les changements de cadrage ne fournissent pas de fenêtres non ambiguës.'
        return report
    report['status']='candidate_format_windows'
    return report


def cached_format_review(source,root,first,last):
    """No source decoder: source identity and sealed cache are checked twice."""
    directory=latest_cache(Path(root),source)
    manifest_path=directory/'manifest.json';encoded=manifest_path.read_bytes()
    identity=source_identity(source)
    cache,count,checksum,integrity=load_cache(directory,source)
    if integrity!='verified_sha256':raise ValueError('Format review requires a sealed cache')
    frames=np.memmap(cache,dtype=np.uint8,mode='r',shape=(count,18,32,3))
    result=plan_format_review(classify_frames(frames),first,last)
    if (hashlib.sha256(cache.read_bytes()).hexdigest()!=checksum
            or manifest_path.read_bytes()!=encoded or source_identity(source)!=identity):
        raise ValueError('Source or discovery cache changed during format review')
    result.update(source=str(source.resolve()),source_identity=identity,cache_sha256=checksum,
                  discovery_manifest=str(manifest_path),original_recording_decoded=False)
    return result
