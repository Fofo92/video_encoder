"""Propose local vidb episode records from a physical DVD menu."""
import argparse
import csv
import io
import json
import re
import signal
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener

from .vidb_project_link import NoRedirect, VidbProjectLink

PROBE = Path(__file__).resolve().with_name('dvd_menu_probe.c')
FFMPEG = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin']


def request_json(path, payload=None, config=None):
    config = config or VidbProjectLink().configuration()
    body = json.dumps(payload).encode('utf-8') if payload is not None else None
    request = Request(f"{config['url']}/encoder_projects/{path}", data=body,
                      headers={'Authorization': f"Bearer {config['token']}", 'Accept': 'application/json',
                               'Content-Type': 'application/json'})
    try:
        with build_opener(NoRedirect()).open(request, timeout=5) as response:
            data = response.read(262_145)
    except HTTPError as error:
        if error.code == 422:
            try:
                detail = json.loads(error.read(4096)).get('error')
            except (ValueError, AttributeError):
                detail = None
            raise ValueError(detail or 'Le catalogue ou la fiche vidb ne peut pas être utilisé.') from error
        raise
    if len(data) > 262_144:
        raise ValueError('Réponse vidb trop volumineuse.')
    return json.loads(data)


def catalogue(ean=None, series_id=None, preparation_id=None):
    if preparation_id is not None:
        return request_json('dvd_menu_catalogue?' + urlencode({'preparation_id': preparation_id}))
    if series_id is not None:
        return request_json('dvd_menu_catalogue?' + urlencode({'series_id': series_id}))
    if not ean or not re.fullmatch(r'[0-9]{13}', ean):
        raise ValueError('Saisis les treize chiffres de l’EAN du coffret.')
    try:
        return request_json(f'dvd_menu_catalogue/{ean}')
    except HTTPError as error:
        if error.code == 404:
            raise ValueError('Cet EAN est inconnu. Relance en saisissant le nom de la série.') from error
        raise


def bind_episode(document, provisional, record_id):
    link = VidbProjectLink()
    config = link.configuration()
    project_id = document['project_id']
    project = {'project_id': project_id, 'project_path': str(provisional.absolute()),
               'output_path': str(provisional.absolute().with_suffix('.mkv')),
               'source_paths': link.source_paths(document)}
    response = request_json('dvd_menu_selection', {'project': project, 'record_id': record_id}, config)
    result = link.checked_response(config, response, project_id)
    if result.get('status') != 'identified' or result.get('record_id') != record_id:
        raise ValueError('vidb n’a pas confirmé la fiche choisie dans le menu DVD.')
    return result


def run(command, timeout=20, data=None):
    result = subprocess.run(command, input=data, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        detail = result.stderr.decode(errors='replace').strip().splitlines()
        raise ValueError(detail[-1] if detail else f'Échec de {Path(command[0]).name}.')
    return result.stdout


def menu_buttons(device, directory):
    binary = directory / 'dvd-menu-probe'
    run(['cc', '-Wall', '-Wextra', '-O2', str(PROBE), '-ldvdnav', '-ldvdread', '-o', str(binary)])
    pages = defaultdict(list)
    for line in run([str(binary), device], timeout=45).decode(errors='replace').splitlines():
        if line.startswith('TITLE\t'):
            vts, unit, pgc, program, button, title, *rectangle = map(int, line.split('\t')[1:])
            pages[(vts, unit, pgc, program)].append((button, title, rectangle))
    return pages


def capture(device, menu, directory):
    vts, unit, pgc, program = map(str, menu)
    pattern = str(directory / 'menu-%02d.png')
    run(FFMPEG + ['-n', '-f', 'dvdvideo', '-menu', '1', '-menu_vts', vts, '-menu_lu', unit,
                  '-pgc', pgc, '-pg', program, '-i', device, '-map', '0:v:0',
                  '-vf', "select='eq(n,0)+gte(t,prev_selected_t+2)'", '-fps_mode', 'vfr',
                  '-t', '6', '-frames:v', '3', pattern])
    return sorted(directory.glob('menu-*.png'))


def normalized(value):
    value = unicodedata.normalize('NFKD', (value or '').casefold())
    return ' '.join(re.findall(r'[a-z0-9]+', ''.join(c for c in value if not unicodedata.combining(c))))


def text_lines(image, threshold):
    filtered = run(FFMPEG + ['-i', str(image), '-vf',
                   f"scale=iw*3:ih*3:flags=lanczos,format=gray,lut=y='if(gte(val,{threshold}),0,255)'",
                   '-frames:v', '1', '-f', 'image2pipe', '-vcodec', 'pgm', '-'])
    ocr = run(['tesseract', 'stdin', 'stdout', '--psm', '11', 'tsv'], data=filtered)
    groups = defaultdict(list)
    for row in csv.DictReader(io.StringIO(ocr.decode()), delimiter='\t'):
        if row['level'] == '5' and row['text'].strip():
            groups[tuple(row[key] for key in ('block_num', 'par_num', 'line_num'))].append(row)
    lines = []
    for words in groups.values():
        left = min(int(w['left']) for w in words)
        top = min(int(w['top']) for w in words)
        right = max(int(w['left']) + int(w['width']) for w in words)
        bottom = max(int(w['top']) + int(w['height']) for w in words)
        lines.append((left, top, right, bottom, ' '.join(w['text'] for w in words)))
    return lines


def joined_lines(lines):
    yield from lines
    for x, y, right, bottom, label in lines:
        for xx, yy, rr, bb, following in lines:
            overlap = min(right, rr) - max(x, xx)
            if 0 <= yy - bottom < max(bottom - y, bb - yy) * 0.8 and overlap > min(right - x, rr - xx) * 0.5:
                yield min(x, xx), y, max(right, rr), bb, label + ' ' + following


def approximate_record(key, lookup):
    if len(key) < 10:
        return None
    scores = defaultdict(float)
    for candidate, records in lookup.items():
        matcher = SequenceMatcher(None, key, candidate)
        if matcher.real_quick_ratio() < 0.68 or matcher.quick_ratio() < 0.68:
            continue
        score = matcher.ratio()
        for record in records:
            scores[record] = max(scores[record], score)
    ranked = sorted(scores, key=scores.get, reverse=True)
    if ranked and scores[ranked[0]] >= 0.82:
        if len(ranked) == 1 or scores[ranked[0]] - scores[ranked[1]] >= 0.15:
            return ranked[0]
    return None


def menu_matches(images, buttons, lookup):
    exact = defaultdict(set)
    approximate = defaultdict(set)
    for image in images:
        for threshold in (135, 145, 155, 165):
            for x, y, right, bottom, text in joined_lines(text_lines(image, threshold)):
                # Capture keeps native DVD pixel coordinates and OCR enlarges by three.
                px, py = (x + right) / 6, (y + bottom) / 6
                hits = [title for _, title, (l, t, r, b) in buttons if l <= px <= r and t <= py <= b]
                if len(hits) != 1:
                    continue
                key = normalized(text)
                records = lookup.get(key)
                if records is not None:
                    exact[hits[0]].update(records)
                    continue
                record = approximate_record(key, lookup)
                if record is not None:
                    approximate[hits[0]].add(record)
    return {**approximate, **exact}


def proposals(device, data):
    records = {row['record_id']: row for row in data['episodes']}
    if not records:
        raise ValueError('Aucun épisode numéroté dans le catalogue de cette série.')
    lookup = defaultdict(set)
    for identity, row in records.items():
        for title in (row['french_title'], row['original_title']):
            if normalized(title):
                lookup[normalized(title)].add(identity)
    evidence = defaultdict(set)
    errors = []
    with tempfile.TemporaryDirectory(prefix='dvd-menu-') as workspace:
        directory = Path(workspace)
        pages = menu_buttons(device, directory)
        ordered = sorted(pages.items(), key=lambda page: -len({button[1] for button in page[1]}))
        targets = {title for buttons in pages.values() for _, title, _ in buttons}
        for index, (menu, buttons) in enumerate(ordered):
            target = directory / str(index)
            target.mkdir()
            try:
                observed = menu_matches(capture(device, menu, target), buttons, lookup)
            except (ValueError, subprocess.TimeoutExpired) as error:
                errors.append(str(error))
                continue
            for title, identities in observed.items():
                evidence[title].update(identities)
            if targets and all(len(evidence[title]) == 1 for title in targets):
                break
    single = {title: next(iter(ids)) for title, ids in evidence.items() if len(ids) == 1}
    counts = Counter(single.values())
    result = [dict(records[record_id], dvd_title=title) for title, record_id in sorted(single.items())
              if counts[record_id] == 1]
    if not result:
        detail = f' {errors[0]}' if errors else ''
        raise ValueError('Aucune correspondance certaine entre le menu et le catalogue.' + detail)
    return {'series_title': data['series_title'], 'episodes': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', nargs='?')
    parser.add_argument('ean', nargs='?')
    parser.add_argument('--search-series')
    parser.add_argument('--series-id', type=int)
    parser.add_argument('--list-preparations', action='store_true')
    parser.add_argument('--preparation-id', type=int)
    args = parser.parse_args()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(130))
    try:
        if args.list_preparations:
            result = request_json('dvd_menu_preparations')
        elif args.search_series is not None:
            result = request_json('dvd_menu_series?' + urlencode({'q': args.search_series}))
        elif args.device:
            result = proposals(args.device, catalogue(args.ean, args.series_id, args.preparation_id))
        else:
            raise ValueError('Indique le lecteur DVD et un coffret ou une série.')
        print(json.dumps(result))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
