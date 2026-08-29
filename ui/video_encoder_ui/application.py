#!/usr/bin/python3

import sys
from pathlib import Path

import mlt7 as mlt
from PySide6 import QtCore, QtGui, QtWidgets
from .shuttle_xpress import ShuttleXpressReader
from .widgets import ClickableSlider, VideoLabel
from .mlt_frame_source import MltFrameSource
from .mlt_audio_player import MltAudioPlayer
from .trim_session import (
    SegmentSelection,
    SourceReference,
    TrimSession,
)
from .segment_list import SegmentListWidget
from .trim_project_bridge import (
    TrimProjectBridge,
    TrimProjectBridgeError,
)
from .trim_project_file_writer import (
    TrimProjectFileWriter,
)

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

        self.source_id = "source"
        self.trim_session = TrimSession()
        self.trim_project_writer = TrimProjectFileWriter(
            TrimProjectBridge()
        )
        self.project_path = None
        self.trim_session.add_source(
            SourceReference(
                identifier=self.source_id,
                path=source_path
            )
        )

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

        self.in_position = None
        self.out_position = None

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

        self.transport_position = 0
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
            QtCore.Qt.AlignmentFlag.AlignVCenter
            | QtCore.Qt.AlignmentFlag.AlignRight
        )
        self.position_label.setMinimumWidth(300)
        self.position_label.setFixedHeight(30)
        self.position_label.setStyleSheet(
            """
            QLabel {
                border-top: 1px solid palette(dark);
                border-left: 1px solid palette(dark);
                border-right: 1px solid palette(light);
                border-bottom: 1px solid palette(light);
                border-radius: 6px;
                background: palette(alternate-base);
                color: palette(text);
                font-family: monospace;
                padding: 0 8px;
            }
            """
        )
        self.shuttle_label = QtWidgets.QLabel()
        self.shuttle_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self.shuttle_label.setFixedSize(88, 30)
        self.update_transport_indicator(0.0)

        self.previous_button = QtWidgets.QPushButton()
        self.previous_button.clicked.connect(
            self.show_previous_frame
        )

        self.next_button = QtWidgets.QPushButton()
        self.next_button.clicked.connect(
            self.show_next_frame
        )

        self.backward_button = QtWidgets.QPushButton()
        self.backward_button.clicked.connect(
            self.accelerate_backward
        )

        self.pause_button = QtWidgets.QPushButton()
        self.pause_button.clicked.connect(
            self.pause_transport
        )

        self.forward_button = QtWidgets.QPushButton()
        self.forward_button.clicked.connect(
            self.accelerate_forward
        )

        self.in_button = QtWidgets.QPushButton("IN")
        self.in_button.clicked.connect(
            self.set_in_marker
        )
        self.in_button.setToolTip(
            "Poser le repère IN sur l’image courante (I)"
        )
        self.in_button.setFixedSize(36, 30)

        self.out_button = QtWidgets.QPushButton("OUT")
        self.out_button.clicked.connect(
            self.set_out_marker
        )
        self.out_button.setToolTip(
            "Poser le repère OUT sur l’image courante (O)"
        )
        self.out_button.setFixedSize(42, 30)

        self.add_segment_button = QtWidgets.QPushButton("+")
        self.add_segment_button.clicked.connect(
            self.add_current_segment
        )
        self.add_segment_button.setToolTip(
            "Ajouter la plage IN/OUT au montage (Entrée)"
        )
        self.add_segment_button.setFixedSize(32, 30)


        marker_button_stylesheet = """
            QPushButton {
                border: 1px solid palette(mid);
                border-radius: 6px;
                background: palette(button);
                font-weight: 600;
                padding: 0 4px;
            }

            QPushButton:hover {
                background: palette(light);
            }

            QPushButton:pressed {
                background: palette(midlight);
            }
        """

        self.in_button.setStyleSheet(
            marker_button_stylesheet
        )
        self.out_button.setStyleSheet(
            marker_button_stylesheet
        )

        self.add_segment_button.setStyleSheet(
            marker_button_stylesheet
        )

        def configure_icon_button(
            button,
            standard_icon,
            tooltip
        ):
            button.setText("")
            button.setIcon(
                self.style().standardIcon(
                    standard_icon
                )
            )
            button.setIconSize(
                QtCore.QSize(22, 22)
            )
            button.setFixedSize(36, 36)

            button.setToolTip(tooltip)
            button.setToolTipDuration(5_000)
            button.setAttribute(
                QtCore.Qt.WidgetAttribute.WA_AlwaysShowToolTips,
                True
            )
            button.setAccessibleName(tooltip)

            button.setStyleSheet(
                """
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 18px;
                    background: palette(button);
                    padding: 0;
                }

                QPushButton:hover {
                    background: palette(light);
                }

                QPushButton:pressed {
                    background: palette(midlight);
                }
                """
            )

        configure_icon_button(
            self.backward_button,
            QtWidgets.QStyle.StandardPixmap.SP_MediaSeekBackward,
            "Réduire la vitesse ou lire en arrière (J)"
        )

        configure_icon_button(
            self.pause_button,
            QtWidgets.QStyle.StandardPixmap.SP_MediaPause,
            "Mettre la lecture en pause (K)"
        )

        configure_icon_button(
            self.forward_button,
            QtWidgets.QStyle.StandardPixmap.SP_MediaSeekForward,
            "Augmenter la vitesse ou lire en avant (L)"
        )

        configure_icon_button(
            self.previous_button,
            QtWidgets.QStyle.StandardPixmap.SP_MediaSkipBackward,
            "Afficher l’image précédente"
        )

        configure_icon_button(
            self.next_button,
            QtWidgets.QStyle.StandardPixmap.SP_MediaSkipForward,
            "Afficher l’image suivante"
        )

        def create_button_group(*buttons):
            group = QtWidgets.QWidget()
            group_layout = QtWidgets.QHBoxLayout(group)
            group_layout.setContentsMargins(0, 0, 0, 0)
            group_layout.setSpacing(0)

            stylesheet = """
                QPushButton {
                    border: 1px solid palette(mid);
                    border-radius: 0;
                    background: palette(button);
                    padding: 0;
                }

                QPushButton[groupPosition="first"] {
                    border-top-left-radius: 6px;
                    border-bottom-left-radius: 6px;
                }

                QPushButton[groupPosition="middle"],
                QPushButton[groupPosition="last"] {
                    border-left: 0;
                }

                QPushButton[groupPosition="last"] {
                    border-top-right-radius: 6px;
                    border-bottom-right-radius: 6px;
                }

                QPushButton:hover {
                    background: palette(light);
                }

                QPushButton:pressed {
                    background: palette(midlight);
                }
            """

            for index, button in enumerate(buttons):
                if index == 0:
                    position = "first"
                elif index == len(buttons) - 1:
                    position = "last"
                else:
                    position = "middle"

                button.setProperty(
                    "groupPosition",
                    position
                )
                button.setStyleSheet(stylesheet)
                group_layout.addWidget(button)

            return group


        def create_vertical_separator():
            separator = QtWidgets.QFrame()
            separator.setFrameShape(
                QtWidgets.QFrame.Shape.VLine
            )
            separator.setFrameShadow(
                QtWidgets.QFrame.Shadow.Sunken
            )
            return separator


        transport_button_group = create_button_group(
            self.backward_button,
            self.pause_button,
            self.forward_button
        )

        frame_button_group = create_button_group(
            self.previous_button,
            self.next_button
        )

        transport_separator = create_vertical_separator()
        markers_separator = create_vertical_separator()
        information_separator = create_vertical_separator()

        def create_marker_label(tooltip):
            label = QtWidgets.QLabel("--:--:--:--")
            label.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignCenter
            )
            label.setFixedSize(94, 30)
            label.setToolTip(tooltip)
            label.setStyleSheet(
                """
                QLabel {
                    border-top: 1px solid palette(dark);
                    border-left: 1px solid palette(dark);
                    border-right: 1px solid palette(light);
                    border-bottom: 1px solid palette(light);
                    border-radius: 6px;
                    background: palette(alternate-base);
                    color: palette(text);
                    font-family: monospace;
                    padding: 0 4px;
                }
                """
            )
            return label


        self.in_marker_label = create_marker_label(
            "Repère IN non défini"
        )
        self.out_marker_label = create_marker_label(
            "Repère OUT non défini"
        )

        markers_widget = QtWidgets.QWidget()
        markers_layout = QtWidgets.QHBoxLayout(
            markers_widget
        )
        markers_layout.setContentsMargins(0, 0, 0, 0)
        markers_layout.setSpacing(4)
        markers_layout.addWidget(self.in_button)
        markers_layout.addWidget(self.in_marker_label)
        markers_layout.addSpacing(6)
        markers_layout.addWidget(self.out_button)
        markers_layout.addWidget(self.out_marker_label)
        markers_layout.addSpacing(6)
        markers_layout.addWidget(
            self.add_segment_button
        )

        markers_widget.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Preferred
        )

        controls_layout = QtWidgets.QHBoxLayout()

        controls_layout.addWidget(
            transport_button_group
        )
        controls_layout.addSpacing(8)
        controls_layout.addWidget(
            frame_button_group
        )

        controls_layout.addWidget(
            transport_separator
        )
        controls_layout.addWidget(
            self.shuttle_label
        )

        controls_layout.addWidget(
            markers_separator
        )
        controls_layout.addWidget(
            markers_widget,
            stretch=0
        )
        controls_layout.addStretch(1)

        controls_layout.addWidget(
            information_separator
        )
        controls_layout.addWidget(
            self.position_label,
            stretch=0
        )
        self.segment_list = SegmentListWidget()
        self.segment_list.segment_selected.connect(
            self.select_segment
        )
        self.segment_list.delete_requested.connect(
            self.delete_segment
        )
        self.segment_list.setVisible(False)


        central_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.position_slider)
        layout.addLayout(controls_layout)
        layout.addWidget(self.segment_list)

        self.setCentralWidget(central_widget)

        self.save_project_action = QtGui.QAction(
            "Enregistrer le projet…",
            self
        )
        self.save_project_action.setShortcut(
            QtGui.QKeySequence.StandardKey.Save
        )
        self.save_project_action.triggered.connect(
            self.save_project
        )

        file_menu = self.menuBar().addMenu("&Fichier")
        file_menu.addAction(
            self.save_project_action
        )

        self.shuttle_reader = None

        try:
            self.shuttle_reader = ShuttleXpressReader(
                SHUTTLE_DEVICE_PATH
            )
        except OSError:
          self.shuttle_label.setText("⏸")
          self.shuttle_label.setToolTip(
              "Transport en pause — "
              "ShuttleXpress indisponible"
          )
        else:
            self.shuttle_reader.jogged.connect(
                self.schedule_wheel_move
            )
        self.shuttle_reader.shuttle_changed.connect(
            self.set_transport_position
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

    def update_transport_indicator(self, speed):
        if speed == 0:
            text = "⏸"
            tooltip = "Transport en pause"
        else:
            if speed < 0:
                symbol = "◀"
                direction = "arrière"
            else:
                symbol = "▶"
                direction = "avant"

            text = f"{symbol}  ×{abs(speed):g}"
            tooltip = (
                f"Lecture {direction} "
                f"à vitesse ×{abs(speed):g}"
            )

        self.shuttle_label.setText(text)
        self.shuttle_label.setToolTip(tooltip)
        self.shuttle_label.setStyleSheet(
            """
            QLabel {
                border-top: 1px solid palette(dark);
                border-left: 1px solid palette(dark);
                border-right: 1px solid palette(light);
                border-bottom: 1px solid palette(light);
                border-radius: 6px;
                background: palette(alternate-base);
                color: palette(text);
                font-weight: 600;
                padding: 0 8px;
            }
            """
        )

    def set_transport_position(self, position):
        self.transport_position = position
        if position == 0:
            self.transport_timer.stop()
            self.stop_audio_playback()

            self.transport_speed = 0.0
            self.transport_frame_remainder = 0.0

            self.shuttle_label.setText("⏸")
            self.shuttle_label.setToolTip(
                "Transport en pause"
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

        self.update_transport_indicator(speed)

    def accelerate_transport(self, direction):
        position = max(
            -max(SHUTTLE_SPEED_BY_POSITION),
            min(
                max(SHUTTLE_SPEED_BY_POSITION),
                self.transport_position + direction
            )
        )

        self.set_transport_position(position)

    def accelerate_backward(self):
        self.accelerate_transport(-1)

    def pause_transport(self):
        self.set_transport_position(0)

    def accelerate_forward(self):
        self.accelerate_transport(1)

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
            _decode_duration_ms
        ) = self.frame_source.frame_at(position)

        self.current_position = actual_position

        if not self.position_slider.isSliderDown():
            self.position_slider.setValue(
                actual_position
            )

        self.video_label.set_image(image)

        self.position_label.setText(
            f"Timecode {self.timecode_for(actual_position)}"
            f"  —  Image {actual_position}"
            f"/{self.frame_source.length - 1}"
        )

    def select_segment(self, index):
        segments = self.trim_session.segments

        if not 0 <= index < len(segments):
            return

        segment = segments[index]

        if segment.source_id != self.source_id:
            return

        self.show_frame(
            segment.start_frame
        )

    def delete_segment(self, index):
        segments = self.trim_session.segments

        if not 0 <= index < len(segments):
            return

        segment = segments[index]

        answer = QtWidgets.QMessageBox.question(
            self,
            "Supprimer le segment",
            "Supprimer le segment "
            f"{index + 1} du montage ?",
            (
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No
            ),
            QtWidgets.QMessageBox.StandardButton.No
        )

        if (
            answer
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return

        self.trim_session.remove_segment(
            segment
        )
        self.refresh_segment_list()

    def refresh_segment_list(self):
        segments = self.trim_session.segments

        rows = [
            (
                index + 1,
                segment.source_id,
                self.timecode_for(
                    segment.start_frame
                ),
                self.timecode_for(
                    segment.end_frame
                ),
                self.timecode_for(
                    segment.end_frame
                    - segment.start_frame
                    + 1
                )
            )
            for index, segment in enumerate(segments)
        ]

        self.segment_list.set_rows(rows)
        self.segment_list.setVisible(
            bool(segments)
        )

        visible_segments = [
            (
                segment.start_frame,
                segment.end_frame
            )
            for segment in segments
            if segment.source_id == self.source_id
        ]

        self.position_slider.set_segments(
            visible_segments
        )

    def clear_active_markers(self):
        self.in_position = None
        self.out_position = None

        self.in_marker_label.setText(
            "--:--:--:--"
        )
        self.in_marker_label.setToolTip(
            "Repère IN non défini"
        )

        self.out_marker_label.setText(
            "--:--:--:--"
        )
        self.out_marker_label.setToolTip(
            "Repère OUT non défini"
        )

        self.position_slider.set_markers(
            None,
            None
        )

    def add_current_segment(self):
        if (
            self.in_position is None
            or self.out_position is None
        ):
            QtWidgets.QMessageBox.information(
                self,
                "Segment incomplet",
                "Pose les repères IN et OUT "
                "avant d’ajouter le segment."
            )
            return

        try:
            segment = SegmentSelection(
                source_id=self.source_id,
                start_frame=self.in_position,
                end_frame=self.out_position
            )
            self.trim_session.add_segment(segment)
        except ValueError as error:
            QtWidgets.QMessageBox.warning(
                self,
                "Segment invalide",
                str(error)
            )
            return

        self.refresh_segment_list()
        self.clear_active_markers()

    def set_in_marker(self):
        position = self.current_position

        if (
            self.out_position is not None
            and position > self.out_position
        ):
            QtWidgets.QMessageBox.warning(
                self,
                "Repère IN invalide",
                "Le repère IN ne peut pas être "
                "placé après le repère OUT."
            )
            return

        self.in_position = position
        self.position_slider.set_markers(
            self.in_position,
            self.out_position
        )
        timecode = self.timecode_for(position)

        self.in_marker_label.setText(timecode)
        self.in_marker_label.setToolTip(
            f"IN : image {position}"
        )

    def set_out_marker(self):
        position = self.current_position

        if (
            self.in_position is not None
            and position < self.in_position
        ):
            QtWidgets.QMessageBox.warning(
                self,
                "Repère OUT invalide",
                "Le repère OUT ne peut pas être "
                "placé avant le repère IN."
            )
            return

        self.out_position = position
        self.position_slider.set_markers(
            self.in_position,
            self.out_position
        )

        timecode = self.timecode_for(position)

        self.out_marker_label.setText(timecode)
        self.out_marker_label.setToolTip(
            f"OUT : image {position}"
        )

    def save_project(self):
        if self.project_path is None:
            suggested_path = Path(
                self.source_path
            ).with_suffix(".json")
        else:
            suggested_path = self.project_path

        selected_path, _selected_filter = (
            QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Enregistrer le projet",
                str(suggested_path),
                (
                    "Projet video_encoder (*.json);;"
                    "Tous les fichiers (*)"
                )
            )
        )

        if not selected_path:
            return

        try:
            destination = self.trim_project_writer.save(
                self.trim_session,
                selected_path
            )
        except (
            OSError,
            ValueError,
            TrimProjectBridgeError
        ) as error:
            QtWidgets.QMessageBox.critical(
                self,
                "Échec de l’enregistrement",
                str(error)
            )
            return

        self.project_path = destination
        self.statusBar().showMessage(
            f"Projet enregistré : {destination}",
            5_000
        )

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            event.accept()
            return

        actions = {
            QtCore.Qt.Key.Key_I: self.set_in_marker,
            QtCore.Qt.Key.Key_O: self.set_out_marker,
            QtCore.Qt.Key.Key_Return: self.add_current_segment,
            QtCore.Qt.Key.Key_Enter: self.add_current_segment,
            QtCore.Qt.Key.Key_J: self.accelerate_backward,
            QtCore.Qt.Key.Key_K: self.pause_transport,
            QtCore.Qt.Key.Key_L: self.accelerate_forward
        }

        action = actions.get(event.key())

        if action is None:
            super().keyPressEvent(event)
            return

        action()
        event.accept()

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
