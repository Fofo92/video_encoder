import shutil
from pathlib import Path


class TrimProjectArchiver:
    def __init__(self, copy_file=shutil.copy2):
        self.copy_file = copy_file

    def archive(self, project_path, output_path):
        source = Path(project_path)
        destination = Path(
            output_path
        ).with_suffix(".json")

        if source.resolve() == destination.resolve():
            return source

        self.copy_file(
            source,
            destination
        )

        return destination
