import json
from pathlib import Path

from .trim_session import (
    SegmentSelection,
    SourceReference,
    TrimSession,
)


class TrimProjectFileReader:
    FORMAT = "video_encoder.trim_project"
    VERSION = 1

    def load(self, path):
        document = json.loads(
            Path(path).read_text(
                encoding="utf-8"
            )
        )

        self.validate(document)

        session = TrimSession()
        source_ids_by_path = {}

        for item in document["timeline"]:
            self.add_item(
                session,
                item,
                source_ids_by_path
            )

        return session

    def validate(self, document):
        if document.get("format") != self.FORMAT:
            raise ValueError(
                "unsupported trim project format"
            )

        if document.get("version") != self.VERSION:
            raise ValueError(
                "unsupported trim project version"
            )

        if not isinstance(
            document.get("timeline"),
            list
        ):
            raise ValueError(
                "trim project timeline is required"
            )

    def add_item(
        self,
        session,
        item,
        source_ids_by_path
    ):
        item_type = item.get("type")

        if item_type == "gap":
            raise ValueError(
                "gaps are not supported by the editor"
            )

        if item_type != "segment":
            raise ValueError(
                "unsupported trim project item"
            )

        source_path = Path(item["source"])
        source_id = source_ids_by_path.get(
            source_path
        )

        if source_id is None:
            source_id = self.add_source(
                session,
                source_path,
                len(source_ids_by_path)
            )
            source_ids_by_path[source_path] = (
                source_id
            )

        session.add_segment(
            SegmentSelection(
                source_id=source_id,
                start_frame=item["start_frame"],
                end_frame=item["end_frame"]
            )
        )

    @staticmethod
    def add_source(session, source_path, index):
        source_id = (
            "source"
            if index == 0
            else f"source_{index}"
        )

        session.add_source(
            SourceReference(
                identifier=source_id,
                path=source_path
            )
        )

        return source_id
