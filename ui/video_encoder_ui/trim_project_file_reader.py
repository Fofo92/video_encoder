import json
from pathlib import Path

from .trim_session import (
    SegmentSelection,
    SourceReference,
    TrimSession,
)


class TrimProjectFileReader:
    FORMAT = "video_encoder.trim_project"
    SUPPORTED_VERSIONS = {1, 2}

    def load(self, path):
        document = json.loads(
            Path(path).read_text(
                encoding="utf-8"
            )
        )

        self.validate(document)

        if document["version"] == 1:
            return self.load_version_1(document)

        return self.load_version_2(document)

    def validate(self, document):
        if document.get("format") != self.FORMAT:
            raise ValueError(
                "unsupported trim project format"
            )

        if (
            document.get("version")
            not in self.SUPPORTED_VERSIONS
        ):
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

        if (
            document["version"] == 2
            and not isinstance(
                document.get("sources"),
                list
            )
        ):
            raise ValueError(
                "trim project sources are required"
            )

    def load_version_1(self, document):
        session = TrimSession()
        source_ids_by_path = {}

        for item in document["timeline"]:
            self.add_version_1_item(
                session,
                item,
                source_ids_by_path
            )

        return session

    def load_version_2(self, document):
        session = TrimSession()

        for source in document["sources"]:
            session.add_source(
                SourceReference(
                    identifier=source["id"],
                    path=Path(source["path"]),
                    inspection=source.get(
                        "inspection"
                    )
                )
            )

        for item in document["timeline"]:
            self.add_version_2_item(
                session,
                item
            )

        return session

    def add_version_1_item(
        self,
        session,
        item,
        source_ids_by_path
    ):
        self.reject_unsupported_item(item)

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

        self.add_segment(
            session,
            item,
            source_id
        )

    def add_version_2_item(
        self,
        session,
        item
    ):
        self.reject_unsupported_item(item)

        self.add_segment(
            session,
            item,
            item["source_id"]
        )

    @staticmethod
    def add_segment(session, item, source_id):
        session.add_segment(
            SegmentSelection(
                source_id=source_id,
                start_frame=item["start_frame"],
                end_frame=item["end_frame"]
            )
        )

    @staticmethod
    def reject_unsupported_item(item):
        item_type = item.get("type")

        if item_type == "gap":
            raise ValueError(
                "gaps are not supported by the editor"
            )

        if item_type != "segment":
            raise ValueError(
                "unsupported trim project item"
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
