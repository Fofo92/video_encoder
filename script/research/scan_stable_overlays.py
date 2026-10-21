"""Bounded full-recording presence scan for an observation-learned graphic.

Research only: observation clips are selected examples, not blind discovery.
No montage, source frame indices, queue changes or deletion are produced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from export_indexed_windows import source_identity
from stable_overlay_signals import (shared_persistent_edges, overlay_candidates,
                                    refine_shared_candidate, presence_scores)


def sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def rgb_blocks(path, log_path, crop=None, max_frames=108000, block_frames=100):
    """Read bounded RGB blocks; always reap the decoder, including cancellation."""
    if crop is None:
        width,height=640,360
        filters='fps=5:start_time=0,scale=640:360,format=rgb24'
    else:
        x,y,width,height=crop
        filters=f'fps=5:start_time=0,scale=640:360,format=rgb24,crop={width}:{height}:{x}:{y}'
    frame_bytes=width*height*3
    with log_path.open('xb') as log:
        process=subprocess.Popen(['ffmpeg','-hide_banner','-nostdin','-v','error','-i',str(path),
                                  '-map','0:v:0','-an','-sn','-dn','-vf',filters,
                                  '-frames:v',str(max_frames+1),'-pix_fmt','rgb24',
                                  '-fps_mode','passthrough','-f','rawvideo','pipe:1'],
                                 stdout=subprocess.PIPE,stderr=log)
        try:
            pending=b'';count=0
            while True:
                part=process.stdout.read(block_frames*frame_bytes-len(pending))
                if part:
                    pending+=part
                    if len(pending)<block_frames*frame_bytes:
                        continue
                if len(pending)%frame_bytes:
                    raise ValueError('Decoder returned an incomplete RGB frame')
                if pending:
                    block=np.frombuffer(pending,dtype=np.uint8).reshape(-1,height,width,3)
                    count+=len(block)
                    if count>max_frames:
                        raise ValueError('Recording exceeds the supported sampling limit; report is incomplete')
                    yield block
                    pending=b''
                if not part:
                    break
            if process.wait()!=0:
                raise RuntimeError(f'Decoder failed; see {log_path}')
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.terminate()
                try:process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill();process.wait()


def padded_crop(shape,bbox,padding=4):
    height,width=shape
    x,y,w,h=bbox
    left,top=max(0,x-padding),max(0,y-padding)
    right,bottom=min(width,x+w+padding),min(height,y+h+padding)
    return [left,top,right-left,bottom-top],[x-left,y-top,w,h]


def learn_model(clips, edge_mode='white'):
    shared=shared_persistent_edges(clips,edge_mode)
    candidates=overlay_candidates(shared)
    if not candidates:
        raise ValueError('No shared persistent graphic in the observations')
    selected=candidates[0]
    refined,peaks=refine_shared_candidate(clips,shared,selected['bbox_xywh'],edge_mode=edge_mode)
    peak_scores=[]
    for clip in clips:
        scores=presence_scores(clip,refined,selected['bbox_xywh'],edge_mode)
        if not np.any(np.convolve((scores>=.8).astype(int),np.ones(3,dtype=int),mode='valid')>=3):
            raise ValueError('The learned graphic has no sustained support in an observation')
        peak_scores.append(float(scores.max()))
    crop,local_bbox=padded_crop(shared.shape,selected['bbox_xywh'])
    x,y,w,h=crop
    return {'mask':refined[y:y+h,x:x+w].copy(),'bbox':local_bbox,'crop':crop,
            'source_shape':list(shared.shape),'candidate_count':len(candidates),
            'training_peak_samples':peaks,'training_peak_scores':peak_scores,
            'edge_mode':edge_mode,'selection':'largest_shared_edge_region; unclassified graphic'}


class PresenceAccumulator:
    """One graphic's streaming state; sample indices survive decoder blocks."""
    def __init__(self,model,threshold=.8,minimum_samples=3):
        if not 0 < threshold <= 1 or type(minimum_samples) is not int or minimum_samples < 1:
            raise ValueError('Invalid graphic presence settings')
        self.model=model;self.threshold=threshold;self.minimum_samples=minimum_samples
        self.count=0;self.active=None;self.intervals=[]

    def close_interval(self):
        if self.active is not None and self.active['end_sample_exclusive']-self.active['first_sample']>=self.minimum_samples:
            self.intervals.append(self.active)
        self.active=None

    def feed(self,block):
        model=self.model
        if block.ndim!=4 or block.dtype!=np.uint8 or block.shape[1:3]!=model['mask'].shape or not len(block):
            raise ValueError('Decoded block does not match the learned crop')
        original_count=len(block)
        if original_count<5:
            block=np.concatenate([block,np.repeat(block[-1:],5-original_count,axis=0)])
        scores=presence_scores(block,model['mask'],model['bbox'],model.get('edge_mode','white'))[:original_count]
        for offset,score in enumerate(scores):
            index=self.count+offset
            if score>=self.threshold:
                if self.active is None:
                    self.active={'first_sample':index,'end_sample_exclusive':index+1,
                                 'peak_sample':index,'peak_score':float(score)}
                else:
                    self.active['end_sample_exclusive']=index+1
                    if score>self.active['peak_score']:
                        self.active.update(peak_sample=index,peak_score=float(score))
            else:self.close_interval()
        self.count+=original_count

    def finish(self):
        self.close_interval()
        return self.count,[{**row,'start_seconds':row['first_sample']/5,
                            'end_seconds_exclusive':row['end_sample_exclusive']/5} for row in self.intervals]


def scan_blocks(blocks, model, progress=None, threshold=.8, minimum_samples=3):
    accumulator=PresenceAccumulator(model,threshold,minimum_samples)
    for block in blocks:
        accumulator.feed(block)
        if progress:progress(accumulator.count)
    return accumulator.finish()


def learn_hypotheses(clips):
    models=[];abstentions={}
    for mode in ['white','contrast']:
        try:models.append(learn_model(clips,edge_mode=mode))
        except ValueError as error:abstentions[mode]=str(error)
    if not models:
        raise ValueError('Neither graphic hypothesis could be learned: '+str(abstentions))
    return models,abstentions


def combined_crop(models):
    if not 1<=len(models)<=2 or len({m['edge_mode'] for m in models})!=len(models):
        raise ValueError('Expected one or two distinct graphic hypotheses')
    if any(m['source_shape']!=models[0]['source_shape'] for m in models):
        raise ValueError('Graphic hypotheses have incompatible source geometry')
    left=min(m['crop'][0] for m in models);top=min(m['crop'][1] for m in models)
    right=max(m['crop'][0]+m['crop'][2] for m in models)
    bottom=max(m['crop'][1]+m['crop'][3] for m in models)
    return [left,top,right-left,bottom-top]


def merge_occurrences(per_mode):
    """Union overlapping sampled signals, retaining every original observation.

    Agreement between these related image tests is not independent evidence.
    No gap between disjoint detections is filled.
    """
    ordered=[]
    for mode,rows in per_mode.items():
        previous=-1
        for row in rows:
            first,last=row.get('first_sample'),row.get('end_sample_exclusive')
            if (type(first) is not int or type(last) is not int or not 0<=first<last
                    or first<previous):
                raise ValueError('Expected ordered disjoint sampled occurrences')
            previous=last
            ordered.append((first,last,mode,row))
    ordered.sort(key=lambda row:(row[0],row[1],row[2]))
    merged=[]
    for first,last,mode,row in ordered:
        evidence={**row,'edge_mode':mode}
        if merged and first<merged[-1]['end_sample_exclusive']:
            current=merged[-1]
            current['end_sample_exclusive']=max(last,current['end_sample_exclusive'])
            current['evidence'].append(evidence)
            current['signal_modes']=sorted(set(current['signal_modes']+[mode]))
        else:
            merged.append({'first_sample':first,'end_sample_exclusive':last,
                           'signal_modes':[mode],'evidence':[evidence],'needs_manual_review':True})
    return [{**row,'start_seconds':row['first_sample']/5,
             'end_seconds_exclusive':row['end_sample_exclusive']/5} for row in merged]


def scan_hypotheses(blocks,models,progress=None):
    crop=combined_crop(models);x,y,width,height=crop
    accumulators=[PresenceAccumulator(model) for model in models]
    count=0
    for block in blocks:
        if block.ndim!=4 or block.shape[1:]!=(height,width,3) or block.dtype!=np.uint8 or not len(block):
            raise ValueError('Decoded block does not match the combined graphic crop')
        for model,accumulator in zip(models,accumulators):
            left,top,w,h=model['crop']
            accumulator.feed(block[:,top-y:top-y+h,left-x:left-x+w])
        count+=len(block)
        if progress:progress(count)
    per_mode={}
    for model,accumulator in zip(models,accumulators):
        model_count,rows=accumulator.finish()
        if model_count!=count:raise ValueError('Graphic hypotheses scanned different sample counts')
        per_mode[model['edge_mode']]=rows
    return count,merge_occurrences(per_mode),per_mode


def verify_aspect(path):
    result=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                           'stream=width,height,sample_aspect_ratio','-of','json',str(path)],
                          capture_output=True,text=True,check=True)
    streams=json.loads(result.stdout).get('streams',[])
    if not streams:
        raise ValueError('No video stream')
    stream=streams[0]
    if (stream.get('sample_aspect_ratio','1:1') not in ['1:1','0:1','N/A']
            or stream['width']*9!=stream['height']*16):
        raise ValueError('This observation scan currently requires square-pixel 16:9 inputs')


def run(source,clip_paths,output,edge_mode='white'):
    if edge_mode not in ('white','contrast','both'):
        raise ValueError('Unknown graphic edge mode')
    source=source.resolve(strict=True)
    paths=[path.resolve(strict=True) for path in clip_paths]
    if not 2<=len(paths)<=6 or len(set(paths))!=len(paths) or source in paths:
        raise ValueError('Use two to six distinct observation clips, separate from the recording')
    if not source.is_file() or any(not path.is_file() for path in paths):
        raise ValueError('Inputs must be regular files')
    output.mkdir(parents=True,exist_ok=False)
    report_path=output/'report.json';started=time.monotonic()
    report={'status':'running','source':str(source),'needs_manual_review':True,
            'sample_fps':5,'source_identity':source_identity(source),'edge_mode':edge_mode}
    def save():
        pending=output/'report.pending'
        pending.write_text(json.dumps(report,indent=2)+'\n')
        pending.replace(report_path)
    save()
    try:
        verify_aspect(source)
        clips=[];identities=[]
        for index,path in enumerate(paths):
            print(f'Observation {index+1}/{len(paths)}',flush=True)
            before=source_identity(path);digest=sha256(path)
            verify_aspect(path)
            blocks=list(rgb_blocks(path,output/f'observation-{index+1}.log',max_frames=300))
            if not blocks:raise ValueError('Empty observation clip')
            clips.append(np.concatenate(blocks))
            identities.append({'path':str(path),'identity':before,'sha256':digest})
        print('Learning the shared graphic from observations...',flush=True)
        if edge_mode=='both':
            models,abstentions=learn_hypotheses(clips)
        else:
            models,abstentions=[learn_model(clips,edge_mode)],{}
        del clips
        for model in models:
            name=f"learned-overlay-{model['edge_mode']}.npz" if edge_mode=='both' else 'learned-overlay.npz'
            np.savez_compressed(output/name,mask=model['mask'],bbox=model['bbox'],crop=model['crop'],edge_mode=model['edge_mode'])
        report.update(stage='scanning',learned_graphics=[{k:v for k,v in m.items() if k!='mask'} for m in models],
                      hypothesis_abstentions=abstentions,observations=identities)
        if edge_mode!='both':report['learned_graphic']=report['learned_graphics'][0]
        save();last_progress=-1
        def progress(count):
            nonlocal last_progress
            if count//300!=last_progress:
                last_progress=count//300
                elapsed=round(time.monotonic()-started)
                print(f'Analysed {count/5:.0f} s of recording; elapsed {elapsed} s',flush=True)
                report.update(sampled_frames=count,elapsed_seconds=elapsed);save()
        blocks=rgb_blocks(source,output/'recording.log',crop=combined_crop(models))
        try:
            count,intervals,per_mode=scan_hypotheses(blocks,models,progress)
        finally:blocks.close()
        if edge_mode!='both':intervals=per_mode[edge_mode]
        if not count:raise ValueError('Empty recording scan')
        if source_identity(source)!=report['source_identity']:
            raise ValueError('Recording changed during scan')
        for observation in identities:
            path=Path(observation['path'])
            if source_identity(path)!=observation['identity'] or sha256(path)!=observation['sha256']:
                raise ValueError('Observation changed during analysis')
        report.update(status='completed',stage='completed',sampled_frames=count,occurrences=intervals,
                      occurrences_by_hypothesis=per_mode,
                      elapsed_seconds=round(time.monotonic()-started),threshold=.8,minimum_samples=3,
                      coordinate_basis='FFmpeg fps=5:start_time=0 timeline; source/editor frame mapping unverified',
                      observation_source_identity_verified=False,
                      limitations=['Learned from selected observations of the same recording, not blind discovery',
                                   'Only the largest shared graphic in the selected edge mode is searched; other separators may be missed',
                                   'Graphic occurrences are not complete jingles or ad intervals',
                                   'Overlapping signals are merged with provenance, not counted as independent confirmations',
                                   'No cut decisions, source-frame conversion, project or queue changes'])
        save()
        return report_path
    except BaseException as error:
        report.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                      error=f'{type(error).__name__}: {error}',elapsed_seconds=round(time.monotonic()-started))
        save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--clips',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--edge-mode',choices=['white','contrast','both'],default='white',
                        help='Research hypothesis; contrast is polarity invariant, not channel or jingle classification')
    args=parser.parse_args()
    print(run(args.source,args.clips,args.output,args.edge_mode))
