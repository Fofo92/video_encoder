import json
from pathlib import Path


class TrimProjectFileWriter:
    def __init__(self, bridge):
        self.bridge = bridge

    def save(self, session, path):
        document = self.bridge.convert(session)
        destination = Path(path)

        destination.write_text(
            json.dumps(
                document,
                ensure_ascii=False,
                indent=2
            )
            + "\n",
            encoding="utf-8"
        )

        return destination
