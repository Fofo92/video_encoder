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


def series_directory(titles, root):
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
        return None
    return matches[0] if len(matches) == 1 else None


def suggested_episode_output(metadata, suggested, root=Path("/videos/Séries TV")):
    try:
        season, episode = int(metadata["season_number"]), int(metadata["episode_number"])
        if not 0 <= season <= 99 or not 1 <= episode <= 999:
            return Path(suggested)
    except (KeyError, TypeError, ValueError):
        return Path(suggested)
    title = title_with_original(metadata)
    title = re.sub(r"[/\\\x00-\x1f]", "_", title).strip(" .")
    title = title.encode("utf-8")[:210].decode("utf-8", errors="ignore")
    if not title:
        return Path(suggested)
    directory = series_directory(metadata.get("series_titles", []), Path(root))
    season_folder = None
    if directory:
        try:
            matches = [p for p in directory.iterdir() if p.is_dir() and not p.is_symlink()
                       and re.fullmatch(rf"Saison 0?{season}(?: \(.*\))?", p.name, re.IGNORECASE)]
        except OSError:
            matches = []
        if len(matches) == 1:
            season_folder = matches[0]
    folder = season_folder or Path(suggested).parent
    return folder / f"S{season:02d} E{episode:02d} - {title}.mkv"
