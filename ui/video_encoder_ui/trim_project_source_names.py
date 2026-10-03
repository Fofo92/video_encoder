from pathlib import Path

from .trim_project_file_reader import (
    TrimProjectFileReader,
)


class TrimProjectSourceNames:
    UNAVAILABLE = "Projet indisponible"
    EMPTY = "Aucune source"

    def __init__(self, reader=None):
        self.reader = (
            reader
            if reader is not None
            else TrimProjectFileReader()
        )
        self.cache = {}

    def __call__(self, project_path):
        project_path = Path(project_path)

        try:
            stat = project_path.stat()
        except OSError:
            return self.UNAVAILABLE

        signature = (
            stat.st_mtime_ns,
            stat.st_size,
        )
        cached = self.cache.get(project_path)

        if (
            cached is not None
            and cached[0] == signature
        ):
            return cached[1]

        names = self.load_names(project_path)
        self.cache[project_path] = (
            signature,
            names,
        )

        return names

    def load_names(self, project_path):
        try:
            session = self.reader.load(
                project_path
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
        ):
            return self.UNAVAILABLE

        names = " · ".join(
            source.path.name
            for source in session.sources
        )

        return names or self.EMPTY
