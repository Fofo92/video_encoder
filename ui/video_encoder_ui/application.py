#!/usr/bin/python3

import sys
from pathlib import Path

import mlt7 as mlt
from PySide6 import QtCore, QtWidgets
from .shuttle_xpress import ShuttleXpressReader
from .widgets import ClickableSlider, VideoLabel
from .mlt_frame_source import MltFrameSource
from .mlt_audio_player import MltAudioPlayer

PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 360
INITIAL_FRAME = 1500

SHUTTLE_DEVICE_PATH = (
    "/dev/input/by-id/"
    "usb-Contour_Design_ShuttleXpress-event-mouse"
)

SHUTTLE_SPEED_BY_POSITION = {
    1: 1.0,
    2: 2.0,
    3: 3.0,
    4: 5.0,
    5: 10.0,
    6: 20.0,
    7: 50.0,
}

class MltFrameMonitor(QtWidgets.QMainWindow):
    def __init__(self, source_path):
        super().__init__()

        self.source_path = source_path

        self.frame_source = MltFrameSource(
            source_path,
            preview_width=PREVIEW_WIDTH,
            preview_height=PREVIEW_HEIGHT
        )
        self.frames_per_second = (
            self.frame_source.frames_per_second
        )

        self.audio_player = MltAudioPlayer(
            source_path
        )

        self.current_position = 0
        self.pending_position = 0
        self.previous_wheel_event_timestamp = None
        self.pending_wheel_position = 0
        self.horizontal_wheel_remainder = 0
        self.vertical_wheel_remainder = 0

        self.wheel_timer = QtCore.QTimer(self)
        self.wheel_timer.setSingleShot(True)
        self.wheel_timer.setInterval(20)
        self.wheel_timer.timeout.connect(
            self.show_pending_wheel_frame
        )
        self.scrub_timer = QtCore.QTimer(self)
        self.scrub_timer.setSingleShot(True)
        self.scrub_timer.setInterval(40)
        self.scrub_timer.timeout.connect(
            self.show_pending_frame
        )

        self.transport_speed = 0.0
        self.transport_frame_remainder = 0.0

        self.transport_clock = QtCore.QElapsedTimer()

        self.transport_timer = QtCore.QTimer(self)
        self.transport_timer.setTimerType(
            QtCore.Qt.TimerType.PreciseTimer
        )
        self.transport_timer.setInterval(40)
        self.transport_timer.timeout.connect(
            self.advance_transport
        )

        self.setWindowTitle(
            "Moniteur d’image MLT — video_encoder"
        )
        self.resize(960, 600)

        self.video_label = VideoLabel()

        self.position_slider = ClickableSlider(
            QtCore.Qt.Orientation.Horizontal
        )

        self.position_slider.setRange(
            0,
            self.frame_source.length - 1
        )
        self.position_slider.sliderMoved.connect(
            self.schedule_scrub
        )
        self.position_slider.sliderReleased.connect(
            self.finish_scrub
        )

        self.position_slider.position_requested.connect(
            self.show_frame
        )

        self.position_label = QtWidgets.QLabel()
        self.position_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.shuttle_label = QtWidgets.QLabel(
            "Transport : pause"
        )
        self.shuttle_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.previous_button = QtWidgets.QPushButton(
            "Image précédente"
        )
        self.previous_button.clicked.connect(
            self.show_previous_frame
        )

        self.next_button = QtWidgets.QPushButton(
            "Image suivante"
        )
        self.next_button.clicked.connect(
            self.show_next_frame
        )

        navigation_layout = QtWidgets.QHBoxLayout()
        navigation_layout.addWidget(self.previous_button)
        navigation_layout.addWidget(self.next_button)

        central_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.position_slider)
        layout.addWidget(self.position_label)
        layout.addWidget(self.shuttle_label)
        layout.addLayout(navigation_layout)

        self.setCentralWidget(central_widget)

        self.shuttle_reader = None

        try:
            self.shuttle_reader = ShuttleXpressReader(
                SHUTTLE_DEVICE_PATH
            )
        except OSError:
            self.shuttle_label.setText(
                "Transport : pause "
                "— ShuttleXpress indisponible"
            )
        else:
            self.shuttle_reader.jogged.connect(
                self.schedule_wheel_move
            )
            self.shuttle_reader.shuttle_changed.connect(
                self.show_shuttle_position
            )

    def schedule_scrub(self, position):
        self.pending_position = position

        if not self.scrub_timer.isActive():
            self.scrub_timer.start()

    def show_pending_frame(self):
        self.show_frame(
            self.pending_position
        )

    def finish_scrub(self):
        self.scrub_timer.stop()
        self.show_frame(
            self.position_slider.value()
        )

    def start_audio_playback(self):
        self.audio_player.start(
            self.current_position
        )

    def stop_audio_playback(self, synchronize=True):
        if self.audio_player is None:
            return

        audio_position = self.audio_player.stop()

        if audio_position is None:
            return

        if (
            synchronize
            and self.frame_source is not None
            and audio_position != self.current_position
        ):
            self.show_frame(audio_position)

    def show_shuttle_position(self, position):
        if position == 0:
            self.transport_timer.stop()
            self.stop_audio_playback()

            self.transport_speed = 0.0
            self.transport_frame_remainder = 0.0

            self.shuttle_label.setText(
                "Transport : pause"
            )
            return

        speed = SHUTTLE_SPEED_BY_POSITION[
            abs(position)
        ]

        if position < 0:
            speed = -speed
        if (
            self.audio_player.is_playing
            and speed != 1.0
        ):

            self.stop_audio_playback()

        self.transport_speed = speed
        self.transport_frame_remainder = 0.0
        self.transport_clock.restart()

        if speed == 1.0:
            self.start_audio_playback()

        if not self.transport_timer.isActive():
            self.transport_timer.start()

        direction = (
            "arrière"
            if speed < 0
            else "avant"
        )

        self.shuttle_label.setText(
            f"Transport : "
            f"{direction} "
            f"×{abs(speed):g}"
        )

    def advance_transport(self):
        if self.transport_speed == 0:
            return

        if self.audio_player.is_playing:
            audio_position = max(
                0,
                min(
                    self.audio_player.position,
                    self.frame_source.length - 1
                )
            )

            if audio_position != self.current_position:
                self.show_frame(audio_position)

            return

        elapsed_seconds = (
            self.transport_clock.restart()
            / 1000
        )

        self.transport_frame_remainder += (
            self.transport_speed
            * self.frames_per_second
            * elapsed_seconds
        )

        frame_count = int(
            self.transport_frame_remainder
        )

        if frame_count == 0:
            return

        self.transport_frame_remainder -= frame_count

        target_position = max(
            0,
            min(
                self.current_position + frame_count,
                self.frame_source.length - 1
            )
        )

        if target_position == self.current_position:
            self.transport_timer.stop()
            return

        self.show_frame(target_position)

    def move_by_frames(self, frame_count):
        self.show_frame(
            self.current_position + frame_count
        )

    def schedule_wheel_move(self, frame_count):
        if self.wheel_timer.isActive():
            base_position = self.pending_wheel_position
        else:
            base_position = self.current_position

        self.pending_wheel_position = max(
            0,
            min(
                base_position + frame_count,
                self.frame_source.length - 1
            )
        )

        if not self.wheel_timer.isActive():
            self.wheel_timer.start()

    def show_pending_wheel_frame(self):
        self.show_frame(
            self.pending_wheel_position
        )

    def show_previous_frame(self):
        self.move_by_frames(-1)

    def show_next_frame(self):
        self.move_by_frames(1)

    def accumulated_wheel_steps(self, axis, delta):
        attribute_name = (
            f"{axis}_wheel_remainder"
        )

        accumulated_delta = (
            getattr(self, attribute_name)
            + delta
        )

        steps = int(
            accumulated_delta / 120
        )

        setattr(
            self,
            attribute_name,
            accumulated_delta - steps * 120
        )

        return steps

    def coarse_wheel_step(self, event_timestamp):
        if self.previous_wheel_event_timestamp is None:
            elapsed_ms = None
        else:
            elapsed_ms = (
                event_timestamp
                - self.previous_wheel_event_timestamp
            )

            if elapsed_ms <= 0:
                elapsed_ms = None

        self.previous_wheel_event_timestamp = (
            event_timestamp
        )

        if elapsed_ms is None or elapsed_ms >= 300:
            return 1

        if elapsed_ms >= 180:
            return 5

        if elapsed_ms >= 100:
            return self.frames_per_second

        if elapsed_ms >= 50:
            return 5 * self.frames_per_second

        return 10 * self.frames_per_second

    def timecode_for(self, position):
        total_seconds, frame_number = divmod(
            position,
            self.frames_per_second
        )
        hours, remainder = divmod(
            total_seconds,
            3600
        )
        minutes, seconds = divmod(
            remainder,
            60
        )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}:"
            f"{frame_number:02d}"
        )

    def show_frame(self, position):
        (
            image,
            actual_position,
            decode_duration_ms
        ) = self.frame_source.frame_at(position)

        self.current_position = actual_position

        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(
                actual_position
            )

        self.video_label.set_image(image)

        self.position_label.setText(
            f"Timecode : "
            f"{self.timecode_for(actual_position)}"
            f"    —    "
            f"Image : {actual_position} "
            f"/ {self.frame_source.length - 1}"
            f"    —    "
            f"Décodage : {decode_duration_ms} ms"
        )

    def wheelEvent(self, event):
        angle = event.angleDelta()

        horizontal_steps = (
            self.accumulated_wheel_steps(
                "horizontal",
                angle.x()
            )
        )
        vertical_steps = (
            self.accumulated_wheel_steps(
                "vertical",
                angle.y()
            )
        )

        shift_pressed = bool(
            event.modifiers()
            & QtCore.Qt.KeyboardModifier.ShiftModifier
        )

        if horizontal_steps:
            self.schedule_wheel_move(
                -horizontal_steps
            )
            event.accept()
            return

        if not vertical_steps:
            event.ignore()
            return

        if shift_pressed:
            frame_count = -vertical_steps
        else:
            frame_count = (
                -vertical_steps
                * self.coarse_wheel_step(
                    event.timestamp()
                )
            )

        self.schedule_wheel_move(frame_count)
        event.accept()

    def shutdown(self):
        self.scrub_timer.stop()
        self.wheel_timer.stop()
        self.transport_timer.stop()

        if self.shuttle_reader is not None:
                self.shuttle_reader.close()
                self.shuttle_reader = None

        self.stop_audio_playback(
            synchronize=False
        )

        if self.audio_player is not None:
            self.audio_player.close()
            self.audio_player = None

        if self.frame_source is not None:
            self.frame_source.close()
            self.frame_source = None

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)


def main():
    if len(sys.argv) != 2:
        print(
            f"Usage: {Path(sys.argv[0]).name} <media>",
            file=sys.stderr
        )
        return 2

    source_path = Path(sys.argv[1]).expanduser().resolve()

    if not source_path.is_file():
        print(
            f"Fichier introuvable : {source_path}",
            file=sys.stderr
        )
        return 2

    factory = mlt.Factory()
    factory.init()

    app = QtWidgets.QApplication(sys.argv)
    window = MltFrameMonitor(source_path)
    window.show()

    QtCore.QTimer.singleShot(
        0,
        lambda: window.show_frame(INITIAL_FRAME)
    )

    try:
        return app.exec()
    finally:
        window.shutdown()
        del window
        factory.close()


if __name__ == "__main__":
    sys.exit(main())
