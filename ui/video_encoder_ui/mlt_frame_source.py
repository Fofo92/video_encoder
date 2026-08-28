import ctypes
import time

import mlt7 as mlt
from PySide6 import QtGui


class MltFrameSource:
    def __init__(
        self,
        source_path,
        preview_width,
        preview_height
    ):
        self.preview_width = preview_width
        self.preview_height = preview_height

        self.profile = mlt.Profile()
        self.producer = mlt.Producer(
            self.profile,
            str(source_path)
        )

        if not self.producer.is_valid():
            raise RuntimeError(
                f"Source MLT invalide : {source_path}"
            )

        self.profile.from_producer(
            self.producer
        )

        self.frame_rate_numerator = (
            self.profile.frame_rate_num()
        )
        self.frame_rate_denominator = (
            self.profile.frame_rate_den()
        )
        self.frames_per_second = round(
            self.frame_rate_numerator
            / self.frame_rate_denominator
        )

    @property
    def length(self):
        return self.producer.get_length()

    def frame_at(self, position):
        position = max(
            0,
            min(
                position,
                self.length - 1
            )
        )

        decode_started_at = time.monotonic()

        self.producer.seek(position)
        frame = self.producer.get_frame()

        image_pointer = frame.fetch_image(
            mlt.mlt_image_rgba,
            self.preview_width,
            self.preview_height
        )

        byte_count = (
            self.preview_width
            * self.preview_height
            * 4
        )

        pixel_data = ctypes.string_at(
            int(image_pointer),
            byte_count
        )

        image = QtGui.QImage(
            pixel_data,
            self.preview_width,
            self.preview_height,
            self.preview_width * 4,
            QtGui.QImage.Format.Format_RGBA8888
        ).copy()

        actual_position = frame.get_position()

        decode_duration_ms = round(
            (
                time.monotonic()
                - decode_started_at
            )
            * 1000
        )

        del image_pointer
        del frame

        return (
            image,
            actual_position,
            decode_duration_ms
        )

    def close(self):
        self.producer = None
        self.profile = None
