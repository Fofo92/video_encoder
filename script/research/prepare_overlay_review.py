"""Prepare decoded-index review windows from graphic groups, never a montage.

Sampled times choose approximate window centres only. Extracted pixels receive
explicit decoded indices; editor alignment and actual cuts still require review.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import time
from export_indexed_windows import source_identity
from group_overlay_occurrences import group_occurrences


def plan(report,start,end,radius=200):
    if type(radius) is not int or not 50<=radius<=500:
        raise ValueError('Review radius must be 50 to 500 decoded frames')
    grouping=group_occurrences(report,start,end)
    groups=[g for g in grouping['groups'] if g['status']=='candidate_temporal_group']
    if not 1<=len(groups)<=6:
        raise ValueError('Expected one to six candidate groups; unresolved graphics remain in the grouping report')
    windows=[]
    for number,group in enumerate(groups,1):
        for role,row in [('departure',group['occurrences'][0]),('resume',group['occurrences'][-1])]:
            centre=round(row['start_seconds']*25)
            first=max(0,centre-radius);last=centre+radius
            windows.append({'name':f'{role}-{number}.mp4','candidate_role':role,
                            'group_index':number,'first_decoded_frame':first,
                            'end_decoded_frame_exclusive':last,'expected_frame_count':last-first,
                            'approximate_graphic_local_frame':centre-first,
                            'centre_planning_basis':'sampled graphic time times 25; approximate, not a cut'})
    if any(a['end_decoded_frame_exclusive']>b['first_decoded_frame'] for a,b in zip(windows,windows[1:])):
        raise ValueError('Review windows overlap; do not infer a montage')
    return grouping,windows


def latest_report(root,source):
    source=source.resolve(strict=True)
    identity=source_identity(source)
    candidates=sorted(root.glob('**/report.json'),key=lambda path:path.stat().st_mtime_ns,reverse=True)
    for path in candidates:
        try:
            r=json.loads(path.read_text())
            if (r.get('status')=='completed' and r.get('sample_fps')==5
                    and r.get('source')==str(source) and r.get('source_identity')==identity
                    and isinstance(r.get('occurrences'),list)):
                return path
        except (OSError,ValueError,TypeError):continue
    raise ValueError('No completed presence report matches the current recording identity')


def file_sha256(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()


def decode_command(source,windows,output):
    labels=''.join(f'[v{i}]' for i in range(len(windows)))
    filters=[f'[0:v:0]split={len(windows)+1}{labels}[monitor]']
    maximum=max(w['end_decoded_frame_exclusive'] for w in windows)
    filters.append(f"[monitor]trim=end_frame={maximum},select='not(mod(n,2500))',scale=16:16,showinfo,nullsink")
    for index,row in enumerate(windows):
        filters.append(f"[v{index}]trim=start_frame={row['first_decoded_frame']}:"
                       f"end_frame={row['end_decoded_frame_exclusive']},"
                       f'settb=1/25,setpts=N,scale=960:-2[out{index}]')
    command=['ffmpeg','-hide_banner','-nostdin','-nostats','-v','info','-n','-i',str(source),
             '-filter_complex_threads','1','-filter_complex',';'.join(filters)]
    for index,row in enumerate(windows):
        command+=['-map',f'[out{index}]','-an','-sn','-dn','-c:v','libx264','-preset','fast','-crf','23',
                  '-r','25','-enc_time_base','1:25','-fps_mode','cfr',str(output/row['name'])]
    return command


def verify_native_rate(source):
    metadata=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
                             'stream=avg_frame_rate','-of','json',str(source)],
                            capture_output=True,text=True,check=True)
    if json.loads(metadata.stdout)['streams'][0]['avg_frame_rate']!='25/1':
        raise ValueError('This decoded-index review pilot requires 25 average fps')


def export(report_path,start,end,output,radius=200):
    encoded=report_path.read_bytes();report=json.loads(encoded)
    grouping,windows=plan(report,start,end,radius)
    source=Path(report['source']).resolve(strict=True)
    if not source.is_file() or source_identity(source)!=report.get('source_identity'):
        raise ValueError('Recording identity differs from the completed presence report; extraction was not started')
    identity=source_identity(source)
    verify_native_rate(source)
    archive=Path(str(output)+'.tar.gz')
    if archive.exists():raise ValueError('Review archive already exists')
    output.mkdir(parents=True,exist_ok=False)
    manifest={'status':'preparing','source':str(source),'source_identity':identity,'fps':25,
              'presence_report_sha256':hashlib.sha256(encoded).hexdigest(),'groups':grouping,
              'windows':windows,'coordinate_basis':'FFmpeg decoded source frame index',
              'editor_alignment':'requires_visual_verification','reviewed_interior_cuts_used':False,
              'limitations':['Approximate sampled times select review windows, never cut indices',
                             'Roles are candidate group endpoints, not established ad boundaries',
                             'No montage, encoding job or source modification']}
    manifest_path=output/'frame-map.json'
    def save():
        pending=output/'frame-map.pending';pending.write_text(json.dumps(manifest,indent=2)+'\n');pending.replace(manifest_path)
    save();started=time.monotonic()
    try:
        with (output/'export.log').open('x') as log:
            process=subprocess.Popen(decode_command(source,windows,output),stdout=subprocess.DEVNULL,
                                     stderr=subprocess.PIPE,text=True)
            try:
                for line in process.stderr:
                    log.write(line)
                    if 'showinfo' in line:
                        match=re.search(r'\bn:\s*(\d+)\s',line)
                        if match:
                            index=int(match.group(1))*2500
                            print(f'Decoded through source frame {index}; elapsed {time.monotonic()-started:.0f} s',flush=True)
                            print('REVIEW_PROGRESS '+json.dumps({'decoded_frame':index}),flush=True)
                if process.wait()!=0:raise RuntimeError(f'Review extraction failed; see {output / "export.log"}')
            finally:
                process.stderr.close()
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
        if source_identity(source)!=identity or report_path.read_bytes()!=encoded:
            raise ValueError('Recording or presence report changed during extraction')
        for row in windows:
            path=output/row['name']
            result=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
                                   '-show_entries','stream=nb_read_frames,avg_frame_rate','-of','json',str(path)],
                                  capture_output=True,text=True,check=True)
            stream=json.loads(result.stdout)['streams'][0]
            if int(stream['nb_read_frames'])!=row['expected_frame_count'] or stream['avg_frame_rate']!='25/1':
                raise ValueError('Review frame count or output frame rate differs; keep diagnostics')
            row['sha256']=file_sha256(path)
        manifest.update(status='export_complete_editor_alignment_unverified',elapsed_seconds=round(time.monotonic()-started))
        save()
        with archive.open('xb') as stream:
            with tarfile.open(fileobj=stream,mode='w:gz') as bundle:
                bundle.add(output,arcname=output.name)
        return archive
    except BaseException as error:
        manifest.update(status='interrupted' if isinstance(error,KeyboardInterrupt) else 'failed',
                        error=f'{type(error).__name__}: {error}')
        save();raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    selector=parser.add_mutually_exclusive_group(required=True)
    selector.add_argument('--report',type=Path)
    selector.add_argument('--latest-scan-for',type=Path)
    parser.add_argument('--search-root',type=Path,default=Path('tmp'))
    parser.add_argument('--programme-start',type=float,required=True)
    parser.add_argument('--programme-end',type=float,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=args.report if args.report else latest_report(args.search_root,args.latest_scan_for)
    print(f'Using presence report: {report}',flush=True)
    print(export(report,args.programme_start,args.programme_end,args.output).resolve())
