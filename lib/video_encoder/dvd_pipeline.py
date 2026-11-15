"""Whole DVD titles: copy locally, encode audio/video, preserve original VobSub timing.

Invoked with argv by Qt and the Ruby queue. No shell interpolation, OCR, or
HandBrake subtitle decoding is used. A queued job never accesses an optical drive.
"""
import argparse
import json
import math
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

FORMAT = 'video_encoder.dvd_project'
VERSION = 2
PROFILE = 'dvd-pal-hevc-v1'


def run(args, capture=False):
    result = subprocess.run([str(arg) for arg in args], check=True, text=True,
                            stdout=subprocess.PIPE if capture else sys.stderr,
                            stderr=subprocess.PIPE if capture else None)
    return result.stdout if capture else None


def positive(value):
    if type(value) is not int or value <= 0:
        raise ValueError('Numéro de titre ou de piste invalide.')
    return value


def seconds(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError('Durée absente ou invalide.')
    return number


def scan(device):
    raw = run(['HandBrakeCLI', '--input', device, '--title', '0', '--scan', '--json'], capture=True)
    marker = 'JSON Title Set:'
    if marker not in raw:
        raise ValueError('HandBrake ne fournit aucun inventaire DVD JSON.')
    data, _ = json.JSONDecoder().raw_decode(raw.rsplit(marker, 1)[1].lstrip())
    titles = data.get('TitleList', [])
    if not titles:
        raise ValueError('Aucun titre DVD lisible.')
    return [{'title': positive(row['Index']), 'duration': seconds(row['Duration']['Ticks'] / 90000),
             'audio': row.get('AudioList', []), 'subtitles': row.get('SubtitleList', [])}
            for row in titles]


def inspect(path, packets=False):
    command = ['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json']
    if packets:
        command += ['-count_packets']
    return json.loads(run(command + [path], capture=True))


def signature(path):
    stat = Path(path).stat()
    if not Path(path).is_file() or stat.st_size <= 0:
        raise ValueError('Copie locale absente ou vide.')
    return {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}


def duration_matches(actual, expected):
    if abs(seconds(actual) - seconds(expected)) > max(3, seconds(expected) * 0.01):
        raise ValueError('La durée obtenue diffère du titre DVD : copie conservée pour vérification.')


def publish(source, destination):
    # Hard-link is atomic and refuses existing files, including broken symlinks.
    os.link(source, destination)
    Path(source).unlink()


def copy_title(device, title, directory, expected_duration):
    title = positive(title)
    directory = Path(directory).absolute()
    directory.mkdir(parents=True, exist_ok=True)
    expected_duration = seconds(expected_duration)
    destination = directory / f'titre-{title:02d}.mkv'
    if os.path.lexists(destination):
        raise ValueError(f'Une copie existe déjà : {destination}')
    with tempfile.TemporaryDirectory(prefix='.dvd-copy-', dir=directory) as work:
        staging = Path(work) / 'source.mkv'
        run(['ffmpeg', '-hide_banner', '-nostdin', '-v', 'error', '-n', '-f', 'dvdvideo',
             '-title', str(title), '-i', device, '-map', '0:v:0', '-map', '0:a',
             '-map', '0:s?', '-c', 'copy', staging])
        details = inspect(staging, packets=True)
        duration_matches(details['format']['duration'], expected_duration)
        if not any(item['codec_type'] == 'video' for item in details['streams']):
            raise ValueError('Copie sans vidéo.')
        publish(staging, destination)
    return {'path': str(destination), 'signature': signature(destination), 'probe': details,
            'dvd_title': title, 'duration': seconds(details['format']['duration'])}


def streams(probe, kind):
    return [item for item in probe['streams'] if item['codec_type'] == kind]


def language(track):
    return str(track.get('tags', {}).get('language', 'und')).lower()


def select_tracks(document, probe):
    audio = document['dvd']['audio']
    subtitles = document['dvd']['subtitles']
    if not isinstance(audio, list) or not 1 <= len(audio) <= 2:
        raise ValueError('Choisis une ou deux pistes audio.')
    if not isinstance(subtitles, list) or len(subtitles) > 2:
        raise ValueError('Sélection de sous-titres invalide.')
    audio_rows = streams(probe, 'audio')
    selected_audio = []
    for selection in audio:
        index = selection['index']
        matches = [row for row in audio_rows if row['index'] == index]
        if type(index) is not int or len(matches) != 1 or selection['role'] not in {'french', 'original'}:
            raise ValueError('Piste audio ou rôle introuvable dans la copie locale.')
        selected_audio.append((audio_rows.index(matches[0]) + 1, matches[0]))
    if len({row['index'] for _, row in selected_audio}) != len(audio):
        raise ValueError('Une même piste audio est sélectionnée deux fois.')
    if len({item['role'] for item in audio}) != len(audio):
        raise ValueError('Les rôles VF et VO doivent être distincts.')
    selected_subtitles = [row for row in streams(probe, 'subtitle') if row['index'] in subtitles]
    if (len(set(subtitles)) != len(subtitles) or len(selected_subtitles) != len(subtitles)
            or any(type(index) is not int for index in subtitles)
            or any(row['codec_name'] != 'dvd_subtitle' for row in selected_subtitles)):
        raise ValueError('Piste de sous-titres DVD introuvable.')
    return selected_audio, selected_subtitles


def load_project(path):
    document = json.loads(Path(path).read_text(encoding='utf-8'))
    if document.get('format') != FORMAT or document.get('version') != VERSION:
        raise ValueError('Projet DVD inconnu.')
    if document['dvd']['profile'] != PROFILE or len(document['sources']) != 1:
        raise ValueError('Profil DVD non pris en charge.')
    source = Path(document['sources'][0]['path'])
    if not source.is_absolute() or str(source).startswith('/dev/') or signature(source) != document['dvd']['signature']:
        raise ValueError('La copie locale a changé ou manque : export arrêté.')
    binding = document.get('vidb', {})
    if (binding.get('status') != 'identified' or not binding.get('binding_token')
            or binding.get('project_id') != document.get('project_id')
            or type(binding.get('record_id')) is not int or binding['record_id'] <= 0):
        raise ValueError('Rattachement vidb à confirmer avant encodage.')
    return document, source


def progress(stage, step):
    print('VIDEO_ENCODER_EXPORT_EVENT ' + json.dumps({'stage': stage, 'step': step, 'total': 2}), flush=True)


def export(project, output, workspace):
    document, source = load_project(project)
    output = Path(output).absolute()
    if output.suffix.lower() != '.mkv' or os.path.lexists(output):
        raise ValueError('Sortie MKV invalide ou déjà présente.')
    probe = inspect(source)
    duration_matches(probe['format']['duration'], document['dvd']['duration'])
    video = streams(probe, 'video')[0]
    rate = video.get('avg_frame_rate', '').split('/')
    if len(rate) != 2 or float(rate[1]) == 0 or abs(float(rate[0]) / float(rate[1]) - 25) > 0.1:
        raise ValueError('Ce premier profil est prévu pour un DVD PAL à 25 images/s.')
    audio, subtitles = select_tracks(document, probe)
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dvd-', dir=workspace) as work:
        work = Path(work)
        encoded = work / 'video-audio.mkv'
        final = work / 'final.mkv'
        progress('video', 1)
        print('DVD : encodage vidéo et audio', flush=True)
        run(['HandBrakeCLI', '--input', source, '--output', encoded, '--format', 'av_mkv',
             '--encoder', 'nvenc_h265', '--quality', '23', '--rate', '25', '--cfr', '--comb-detect',
             '--decomb', '--crop-mode', 'none', '--maxHeight', '720', '--audio',
             ','.join(str(number) for number, _ in audio), '--aencoder', ','.join(['av_aac'] * len(audio)),
             '--ab', ','.join(['160'] * len(audio)), '--subtitle', 'none', '--markers'])
        progress('remux', 2)
        print('DVD : réintégration des sous-titres originaux', flush=True)
        command = ['ffmpeg', '-hide_banner', '-nostdin', '-v', 'error', '-n', '-i', encoded,
                   '-i', source, '-map', '0:v:0', '-map', '0:a']
        for row in subtitles:
            command += ['-map', f"1:{row['index']}"]
        command += ['-map_chapters', '0', '-c', 'copy']
        for index, (_, row) in enumerate(audio):
            command += [f'-metadata:s:a:{index}', f'language={language(row)}']
        for index, row in enumerate(subtitles):
            command += [f'-metadata:s:s:{index}', f'language={language(row)}', f'-disposition:s:{index}', '0']
        run(command + [final])
        validate_output(inspect(final), probe, audio, subtitles)
        if signature(source) != document['dvd']['signature']:
            raise ValueError('La copie source a changé pendant l’encodage.')
        publish(final, output)
    try:
        workspace.rmdir()
    except OSError:
        pass
    print('DVD : export terminé', flush=True)


def validate_output(probe, source_probe, audio, subtitles):
    duration_matches(probe['format']['duration'], source_probe['format']['duration'])
    actual_audio = streams(probe, 'audio')
    actual_subtitles = streams(probe, 'subtitle')
    if (len(streams(probe, 'video')) != 1 or len(actual_audio) != len(audio)
            or len(actual_subtitles) != len(subtitles)
            or [language(row) for row in actual_audio] != [language(row) for _, row in audio]
            or [language(row) for row in actual_subtitles] != [language(row) for row in subtitles]):
        raise ValueError('Les pistes finales ne correspondent pas à la sélection : sortie non publiée.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    scanner = commands.add_parser('scan')
    scanner.add_argument('device')
    copier = commands.add_parser('copy')
    copier.add_argument('device')
    copier.add_argument('title', type=int)
    copier.add_argument('directory')
    copier.add_argument('duration', type=float)
    encoder = commands.add_parser('export')
    encoder.add_argument('project')
    encoder.add_argument('output')
    encoder.add_argument('workspace')
    args = parser.parse_args()
    try:
        if args.command == 'scan':
            print(json.dumps(scan(args.device)))
        elif args.command == 'copy':
            print(json.dumps(copy_title(args.device, args.title, args.directory, args.duration)))
        else:
            export(args.project, args.output, args.workspace)
    except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
        # Never print a project document: it contains a vidb binding token.
        message = error.stderr if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print(str(message)[-8000:], file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    # SIGTERM from the GUI cancels the entire helper process group. Unwind the
    # temporary-directory context after the child has received the same signal.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(130))
    sys.exit(main())
