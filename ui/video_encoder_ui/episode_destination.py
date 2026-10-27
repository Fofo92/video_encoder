"""Suggest episode destinations using an unambiguous existing series directory."""
import re
import unicodedata
from pathlib import Path

from .title_convention import title_with_original


def key(value):
    plain = unicodedata.normalize("NFKD", value).encode("ascii", errors="ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", plain.casefold())


def series_key(name):
    return key(re.sub(r"\s*\([^()]*\d[^()]*\)\s*$", "", name))


def series_directories(titles, root):
    expected = {key(title) for title in titles if isinstance(title, str) and title.strip()}
    matches = []
    try:
        parents = [root] + [root / name for name in ("_complet", "_incomplet")]
        for parent in parents:
            if not parent.is_dir():
                continue
            for folder in parent.iterdir():
                if folder.name.startswith("_") or not folder.is_dir() or folder.is_symlink():
                    continue
                name = re.sub(r"\s*\([^()]*\d[^()]*\)\s*$", "", folder.name)
                alternatives = {key(name), key(name.split(" (")[0])}
                if expected & alternatives:
                    matches.append(folder)
    except OSError:
        return []
    return matches


def series_directory(titles, root):
    matches = series_directories(titles, root)
    return matches[0] if len(matches) == 1 else None


def proposed_series_directory(metadata, root):
    french = str(metadata.get('series_french_title') or '').strip()
    original = str(metadata.get('series_original_title') or '').strip()
    year = metadata.get('series_year')
    if not french or not isinstance(year, int) or not 1800 <= year <= 2200:
        return None
    name = f'{french} ({original}) ({year})' if original else f'{french} ({year})'
    name = re.sub(r'[/\\\x00-\x1f]', '_', name).strip(' .')
    name = name.encode('utf-8')[:220].decode('utf-8', errors='ignore')
    return Path(root) / name if name else None


def episode_title(metadata):
    french = str(metadata.get('french_title') or '')
    original = str(metadata.get('original_title') or '')
    local = re.fullmatch(r'episode\s*(\d+)', key(french))
    native = re.fullmatch(r'(?:episode|dil)\s*(\d+)', key(original))
    if local and native and local[1] == native[1]:
        return french
    return title_with_original(metadata)


def suggested_episode_output(metadata, suggested, root=Path("/videos/Séries TV")):
    try:
        season, episode = int(metadata["season_number"]), int(metadata["episode_number"])
        if not 0 <= season <= 99 or not 1 <= episode <= 999:
            return Path(suggested)
    except (KeyError, TypeError, ValueError):
        return Path(suggested)
    title = episode_title(metadata)
    title = re.sub(r"[/\\\x00-\x1f]", "_", title).strip(" .")
    title = title.encode("utf-8")[:210].decode("utf-8", errors="ignore")
    if not title:
        return Path(suggested)
    matches = series_directories(metadata.get("series_titles", []), Path(root))
    directory = matches[0] if len(matches) == 1 else None
    if not matches and Path(suggested).parent in {Path('/videos'), Path(root)}:
        directory = proposed_series_directory(metadata, root)
    season_folder = None
    if directory:
        try:
            matches = [p for p in directory.iterdir() if p.is_dir() and not p.is_symlink()
                       and re.fullmatch(rf"Saison 0?{season}(?: \(.*\))?", p.name, re.IGNORECASE)]
        except OSError:
            matches = []
        if len(matches) == 1:
            season_folder = matches[0]
    if directory:
        folder = season_folder or directory / f"Saison {season:02d}"
    else:
        folder = Path(root) if Path(suggested).parent == Path("/videos") else Path(suggested).parent
    return folder / f"S{season:02d} E{episode:02d} - {title}.mkv"
