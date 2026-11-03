"""Keep the selected vidb collection or direct series in the suggested path."""
import re
from pathlib import Path

from .episode_destination import series_directories
from .title_convention import title_with_original


def container_directory(metadata, root):
    container = metadata.get("destination_container")
    if not isinstance(container, dict) or container.get("record_kind") not in {"collection", "series"}:
        return Path(root)
    title = title_with_original(container)
    name = re.sub(r"[/\\\x00-\x1f]", "_", title).strip(" .")
    name = name.encode("utf-8")[:220].decode("utf-8", errors="ignore")
    if not name:
        return Path(root)
    titles = [container.get("french_title"), container.get("original_title"), title]
    matches = series_directories(titles, Path(root))
    return matches[0] if len(matches) == 1 else Path(root) / name
