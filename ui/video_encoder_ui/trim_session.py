from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceReference:
    identifier: str
    path: Path

    def __post_init__(self):
        if not self.identifier:
            raise ValueError(
                "source identifier is required"
            )

        object.__setattr__(
            self,
            "path",
            Path(self.path)
        )


@dataclass(frozen=True)
class SegmentSelection:
    source_id: str
    start_frame: int
    end_frame: int

    def __post_init__(self):
        if not self.source_id:
            raise ValueError(
                "segment source is required"
            )

        if self.start_frame < 0:
            raise ValueError(
                "start frame must not be negative"
            )

        if self.end_frame <= self.start_frame:
            raise ValueError(
                "end frame must be after start frame"
            )


class TrimSession:
    FORMAT = "video_encoder.trim_session"
    VERSION = 1

    def __init__(self):
        self._sources = {}
        self._segments = []

    @property
    def sources(self):
        return tuple(self._sources.values())

    @property
    def segments(self):
        return tuple(self._segments)

    def add_source(self, source):
        if source.identifier in self._sources:
            raise ValueError(
                "source identifier is already used"
            )

        self._sources[source.identifier] = source

    def add_segment(self, segment):
        if segment.source_id not in self._sources:
            raise ValueError(
                "segment source is unknown"
            )

        self._segments.append(segment)
        return segment

    def remove_segment(self, segment):
        self._segments.remove(segment)

    def to_document(self):
        return {
            "format": self.FORMAT,
            "version": self.VERSION,
            "sources": [
                {
                    "id": source.identifier,
                    "path": str(source.path)
                }
                for source in self.sources
            ],
            "timeline": [
                {
                    "source_id": segment.source_id,
                    "start_frame": segment.start_frame,
                    "end_frame": segment.end_frame
                }
                for segment in self.segments
            ]
        }
