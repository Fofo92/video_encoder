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


def scan_blocks(blocks, model, progress=None, threshold=.8, minimum_samples=3):
    if not 0 < threshold <= 1 or type(minimum_samples) is not int or minimum_samples < 1:
        raise ValueError('Invalid graphic presence settings')
    count=0;active=None;intervals=[]
    def finish():
        nonlocal active
        if active is not None and active['end_sample_exclusive']-active['first_sample']>=minimum_samples:
            intervals.append(active)
        active=None
    for block in blocks:
        if block.ndim!=4 or block.dtype!=np.uint8 or block.shape[1:3]!=model['mask'].shape or not len(block):
            raise ValueError('Decoded block does not match the learned crop')
        original_count=len(block)
        if original_count<5:
            block=np.concatenate([block,np.repeat(block[-1:],5-original_count,axis=0)])
        scores=presence_scores(block,model['mask'],model['bbox'],model.get('edge_mode','white'))[:original_count]
        for offset,score in enumerate(scores):
            index=count+offset
            if score>=threshold:
                if active is None:
                    active={'first_sample':index,'end_sample_exclusive':index+1,
                            'peak_sample':index,'peak_score':float(score)}
                else:
                    active['end_sample_exclusive']=index+1
                    if score>active['peak_score']:
                        active.update(peak_sample=index,peak_score=float(score))
            else:finish()
        count+=original_count
        if progress:progress(count)
    finish()
    return count,[{**row,'start_seconds':row['first_sample']/5,
                   'end_seconds_exclusive':row['end_sample_exclusive']/5} for row in intervals]


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
    if edge_mode not in ('white','contrast'):
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
        model=learn_model(clips,edge_mode)
        del clips
        np.savez_compressed(output/'learned-overlay.npz',mask=model['mask'],bbox=model['bbox'],crop=model['crop'],edge_mode=edge_mode)
        report.update(stage='scanning',learned_graphic={k:v for k,v in model.items() if k!='mask'},observations=identities)
        save();last_progress=-1
        def progress(count):
            nonlocal last_progress
            if count//300!=last_progress:
                last_progress=count//300
                elapsed=round(time.monotonic()-started)
                print(f'Analysed {count/5:.0f} s of recording; elapsed {elapsed} s',flush=True)
                report.update(sampled_frames=count,elapsed_seconds=elapsed);save()
        blocks=rgb_blocks(source,output/'recording.log',crop=model['crop'])
        try:count,intervals=scan_blocks(blocks,model,progress)
        finally:blocks.close()
        if not count:raise ValueError('Empty recording scan')
        if source_identity(source)!=report['source_identity']:
            raise ValueError('Recording changed during scan')
        for observation in identities:
            path=Path(observation['path'])
            if source_identity(path)!=observation['identity'] or sha256(path)!=observation['sha256']:
                raise ValueError('Observation changed during analysis')
        report.update(status='completed',stage='completed',sampled_frames=count,occurrences=intervals,
                      elapsed_seconds=round(time.monotonic()-started),threshold=.8,minimum_samples=3,
                      coordinate_basis='FFmpeg fps=5:start_time=0 timeline; source/editor frame mapping unverified',
                      observation_source_identity_verified=False,
                      limitations=['Learned from selected observations of the same recording, not blind discovery',
                                   'Only the largest shared graphic in the selected edge mode is searched; other separators may be missed',
                                   'Graphic occurrences are not complete jingles or ad intervals',
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
    parser.add_argument('--edge-mode',choices=['white','contrast'],default='white',
                        help='Research hypothesis; contrast is polarity invariant, not channel or jingle classification')
    args=parser.parse_args()
    print(run(args.source,args.clips,args.output,args.edge_mode))
