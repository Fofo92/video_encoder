"""Validate existing extraction clips as observations, never as reference cuts."""
import hashlib
import json
from pathlib import Path
import subprocess
from export_indexed_windows import source_identity


def observations_from_manifest(path,source,bounds):
    path=path.resolve(strict=True);encoded=path.read_bytes();data=json.loads(encoded)
    source=source.resolve(strict=True)
    if Path(data['source']).resolve()!=source or data.get('source_identity')!=source_identity(source):
        raise ValueError('Observation extraction does not match the unchanged source')
    windows=data.get('windows')
    if not isinstance(windows,list) or len(windows)>24:
        raise ValueError('Expected a bounded list of extraction windows')
    clips=[];seen=set()
    for window in windows:
        first,last=window.get('first_decoded_frame'),window.get('end_decoded_frame_exclusive')
        if type(first) is not int or type(last) is not int or not 0<=first<last:
            raise ValueError('Invalid observation window indices')
        if first<bounds[0] or last>bounds[1]+1:
            continue
        name=window['name']
        if not isinstance(name,str) or Path(name).name!=name or name in seen:
            raise ValueError('Expected distinct local observation clip names')
        seen.add(name);clip=(path.parent/name).resolve(strict=True)
        if clip.parent!=path.parent or not clip.is_file() or not 25<=last-first<=1500:
            raise ValueError('Invalid observation clip path or duration')
        metadata=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0',
                                 '-show_entries','stream=avg_frame_rate,nb_read_frames','-of','json',str(clip)],
                                capture_output=True,text=True,check=True)
        streams=json.loads(metadata.stdout).get('streams',[])
        if (not streams or streams[0].get('avg_frame_rate')!='25/1'
                or int(streams[0].get('nb_read_frames',-1))!=last-first):
            raise ValueError('An observation clip is truncated or has incompatible frame timing')
        if window.get('sha256'):
            digest=hashlib.sha256(clip.read_bytes()).hexdigest()
            if digest!=window['sha256']:raise ValueError('Observation clip checksum differs')
        clips.append(clip)
    if not 2<=len(clips)<=6:
        raise ValueError('Expected two to six complete observation clips inside the programme')
    if path.read_bytes()!=encoded:
        raise ValueError('Observation extraction manifest changed during validation')
    return clips,hashlib.sha256(encoded).hexdigest()
