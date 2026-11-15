"""Persistent DVD preparation, independent from Qt and optical-drive lifetime."""
import json
import os
import uuid
from pathlib import Path

FORMAT = 'video_encoder.dvd_project'
PROFILE = 'dvd-pal-hevc-v1'


def new_project(copied, audio, subtitles):
    return {'format': FORMAT, 'version': 2, 'project_id': str(uuid.uuid4()),
            'sources': [{'id': 'source', 'path': copied['path']}],
            'dvd': {'profile': PROFILE, 'title': copied['dvd_title'],
                    'signature': copied['signature'], 'duration': copied['duration'],
                    'audio': audio, 'subtitles': subtitles}}


def write_new(path, document):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation: a previous project or a symlink must never be replaced.
    with path.open('x', encoding='utf-8') as target:
        try:
            json.dump(document, target, ensure_ascii=False, indent=2)
            target.write('\n')
            target.flush()
            os.fsync(target.fileno())
        except BaseException:
            path.unlink()
            raise


def provisional_output(title, episodic, season, episode):
    title = ''.join('_' if char in '/\\' or ord(char) < 32 else char for char in title).strip(' .')
    if not title:
        raise ValueError('Indique le titre de l’œuvre à rechercher dans vidb.')
    if episodic:
        title += f' - S{season:02d} E{episode:02d}'
    title = title.encode('utf-8')[:210].decode('utf-8', errors='ignore')
    return Path('/videos') / f'{title}.mkv'


def audio_defaults(rows):
    ordinary = [row for row in rows if not row.get('disposition', {}).get('visual_impaired')]
    french = [row for row in ordinary if row.get('tags', {}).get('language') in {'fra', 'fre', 'fr'}]
    original = [row for row in ordinary if row.get('tags', {}).get('language', 'und')
                not in {'fra', 'fre', 'fr', 'und', 'qaa'}]
    return (french[0]['index'] if len(french) == 1 else None,
            original[0]['index'] if len(original) == 1 else None)


def subtitle_default(rows):
    french = [row for row in rows if row.get('tags', {}).get('language') in {'fra', 'fre', 'fr'}]
    # Packet count distinguishes a nearly empty forced track from full subtitles.
    # The user still confirms: disc order does not identify hearing-impaired tracks.
    return max(french, key=packet_count)['index'] if french else None


def packet_count(row):
    try:
        return int(row.get('nb_read_packets') or 0)
    except (TypeError, ValueError):
        return 0
