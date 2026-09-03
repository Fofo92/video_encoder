#!/usr/bin/python3

import sys
import tempfile
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
from .trim_project_exporter import (
    TrimProjectExporter,
)
from .audio_preflight_runner import AudioPreflightRunner
from .trim_project_file_reader import (
    TrimProjectFileReader,
)
from .trim_export_queue_client import (
    TrimExportQueueClient,
    TrimExportQueueError,
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
    def __init__(
        self,
        source_path,
        trim_session=None,
        project_path=None
    ):

        super().__init__()

        self.source_path = Path(source_path)
        self.trim_session = (
            trim_session
            if trim_session is not None
            else TrimSession()
        )

        if trim_session is None:
            self.source_id = "source"
            self.trim_session.add_source(
                SourceReference(
                    identifier=self.source_id,
                    path=self.source_path
                )
            )
        else:
            sources = self.trim_session.sources

            if len(sources) != 1:
                raise ValueError(
                    "the editor requires exactly one source"
                )

            self.source_id = sources[0].identifier

        self.trim_project_writer = TrimProjectFileWriter(
            TrimProjectBridge()
        )
        self.project_path = (
            Path(project_path)
            if project_path is not None
            else None
        )

        self.audio_preflight_runner = AudioPreflightRunner()
        self.pending_export = None
        self.pending_export_mode = None
        self.trim_export_queue_client = (
            TrimExportQueueClient()
        )

        self.close_after_preflight = False
        self.audio_preflight_cancel_prompt_active = False
        self.deferred_audio_preflight_result = None

        self.audio_preflight_runner.failed.connect(
            self.audio_preflight_failed
        )
        self.audio_preflight_runner.succeeded.connect(
            self.audio_preflight_succeeded
        )
        self.audio_preflight_runner.status_changed.connect(
            self.audio_preflight_status_changed
        )
        self.trim_project_exporter = (
            TrimProjectExporter()
        )
        self.trim_project_exporter.status_changed.connect(
            self.export_status_changed
        )

        self.export_warnings = []

        self.export_warning_label = QtWidgets.QLabel(self)
        self.export_warning_label.setTextFormat(
            QtCore.Qt.TextFormat.PlainText
        )
        self.export_warning_label.setVisible(False)

        self.statusBar().addPermanentWidget(
            self.export_warning_label
        )

        self.trim_project_exporter.warning_received.connect(
            self.export_warning_received
        )
        self.trim_project_exporter.succeeded.connect(
            self.export_succeeded
        )
        self.trim_project_exporter.failed.connect(
            self.export_failed
        )
        self.trim_project_exporter.progress_changed.connect(
            self.export_progress_changed
        )

        self.trim_project_exporter.stage_changed.connect(
            self.export_stage_changed
        )

        self.export_status = "idle"

        self.export_stage = None
        self.export_step = 0
        self.export_total_steps = 0
        self.export_stage_label = ""

        self.export_elapsed_clock = QtCore.QElapsedTimer()

        self.export_elapsed_timer = QtCore.QTimer(self)
        self.export_elapsed_timer.setInterval(1_000)
        self.export_elapsed_timer.timeout.connect(
            self.update_export_elapsed
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

        self.update_window_title()
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

        self.export_progress_bar = (
            QtWidgets.QProgressBar()
        )
        self.export_progress_bar.setRange(
            0,
            100
        )
        self.export_progress_bar.setValue(0)
        self.export_progress_bar.setFormat(
            "Encodage — %p %"
        )
        self.export_progress_bar.setVisible(False)


        central_widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.position_slider)
        layout.addLayout(controls_layout)
        layout.addWidget(self.segment_list)

        layout.addWidget(
            self.export_progress_bar
        )

        self.setCentralWidget(central_widget)

        def themed_icon(name, fallback):
            icon = QtGui.QIcon.fromTheme(name)

            if icon.isNull():
                icon = self.style().standardIcon(
                    fallback
                )

            return icon

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

        def export_video_icon():
            icon_size = QtCore.QSize(32, 32)

            export_icon = themed_icon(
                "document-export",
                QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton
            )
            video_icon = themed_icon(
                "video-x-generic",
                QtWidgets.QStyle.StandardPixmap.SP_MediaPlay
            )

            pixmap = export_icon.pixmap(
                icon_size
            )

            painter = QtGui.QPainter(
                pixmap
            )
            painter.setRenderHint(
                QtGui.QPainter.RenderHint.Antialiasing,
                True
            )

            video_pixmap = video_icon.pixmap(
                QtCore.QSize(10, 10)
            )
            video_pixmap = video_pixmap.scaled(
                10,
                13,
                QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )

            tint_painter = QtGui.QPainter(
                video_pixmap
            )
            tint_painter.setCompositionMode(
                QtGui.QPainter.CompositionMode.CompositionMode_SourceIn
            )
            tint_painter.fillRect(
                video_pixmap.rect(),
                self.palette().color(
                    QtGui.QPalette.ColorRole.WindowText
                )
            )
            tint_painter.end()

            painter.drawPixmap(
                QtCore.QRect(
                    7,
                    11,
                    10,
                    13
                ),
                video_pixmap
            )

            painter.end()

            return QtGui.QIcon(
                pixmap
            )

        def queue_video_icon():
            icon_size = QtCore.QSize(32, 32)
            pixmap = export_video_icon().pixmap(
                icon_size
            )

            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(
                QtGui.QPainter.RenderHint.Antialiasing,
                True
            )

            badge_rectangle = QtCore.QRect(
                15,
                15,
                17,
                17
            )

            badge_pen = QtGui.QPen(
                self.palette().color(
                    QtGui.QPalette.ColorRole.Window
                ),
                1
            )
            painter.setPen(badge_pen)
            painter.setBrush(
                self.palette().color(
                    QtGui.QPalette.ColorRole.Highlight
                )
            )
            painter.drawEllipse(badge_rectangle)

            plus_pen = QtGui.QPen(
                self.palette().color(
                    QtGui.QPalette.ColorRole.HighlightedText
                ),
                3
            )
            plus_pen.setCapStyle(
                QtCore.Qt.PenCapStyle.RoundCap
            )
            painter.setPen(plus_pen)

            painter.drawLine(
                QtCore.QPoint(19, 23),
                QtCore.QPoint(28, 23)
            )
            painter.drawLine(
                QtCore.QPoint(23, 19),
                QtCore.QPoint(23, 28)
            )

            painter.end()

            return QtGui.QIcon(pixmap)

        def save_json_icon():
            icon_size = QtCore.QSize(32, 32)

            document_icon = themed_icon(
                "document-export",
                QtWidgets.QStyle.StandardPixmap.SP_DialogApplyButton
            )

            pixmap = document_icon.pixmap(
                icon_size
            )

            painter = QtGui.QPainter(
                pixmap
            )
            painter.setRenderHint(
                QtGui.QPainter.RenderHint.Antialiasing,
                True
            )

            symbol_rectangle = QtCore.QRectF(
                6,
                10,
                15,
                13
            )

            font = QtGui.QFontDatabase.systemFont(
                QtGui.QFontDatabase.SystemFont.FixedFont
            )
            font.setBold(True)
            font.setPixelSize(9)

            painter.setFont(font)

            painter.setPen(
                self.palette().color(
                    QtGui.QPalette.ColorRole.Base
                )
            )

            for horizontal_offset, vertical_offset in (
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1)
            ):
                painter.drawText(
                    symbol_rectangle.translated(
                        horizontal_offset,
                        vertical_offset
                    ),
                    QtCore.Qt.AlignmentFlag.AlignCenter,
                    "{}"
                )

            painter.setPen(
                self.palette().color(
                    QtGui.QPalette.ColorRole.WindowText
                )
            )
            painter.drawText(
                symbol_rectangle,
                QtCore.Qt.AlignmentFlag.AlignCenter,
                "{}"
            )

            painter.end()

            return QtGui.QIcon(
                pixmap
            )

        self.save_project_action.setIcon(
            save_json_icon()
        )
        self.save_project_action.setToolTip(
            "Enregistrer le projet JSON (Ctrl+S)"
        )
        self.save_project_action.setStatusTip(
            "Enregistrer le projet de montage au format JSON"
        )

        self.export_project_action = QtGui.QAction(
            "Exporter le montage…",
            self
        )
        self.export_project_action.setShortcut(
            QtGui.QKeySequence("Ctrl+E")
        )
        self.export_project_action.triggered.connect(
            self.export_project
        )

        self.export_project_action.setIcon(
            export_video_icon()
        )
        self.export_project_action.setToolTip(
            "Encoder le montage (Ctrl+E)"
        )
        self.export_project_action.setStatusTip(
            "Encoder le montage dans un fichier MKV"
        )

        self.queue_export_action = QtGui.QAction(
            "Ajouter le montage à la file…",
            self,
        )
        self.queue_export_action.setShortcut(
            QtGui.QKeySequence("Ctrl+Shift+E")
        )
        self.queue_export_action.triggered.connect(
            lambda _checked=False: self.export_project(
                queued=True
            )
        )
        self.queue_export_action.setIcon(
            queue_video_icon()
        )
        self.queue_export_action.setToolTip(
            "Ajouter le montage à la file "
            "(Ctrl+Shift+E)"
        )
        self.queue_export_action.setStatusTip(
            "Contrôler puis ajouter le montage "
            "à la file d’export"
        )

        self.cancel_export_action = QtGui.QAction(
            "Annuler l’export",
            self
        )
        self.cancel_export_action.setIcon(
            themed_icon(
                "process-stop",
                QtWidgets.QStyle.StandardPixmap.SP_BrowserStop
            )
        )
        self.cancel_export_action.setToolTip(
            "Annuler l’encodage en cours"
        )
        self.cancel_export_action.setStatusTip(
            "Interrompre le processus d’encodage en cours"
        )
        self.cancel_export_action.setEnabled(False)
        self.cancel_export_action.triggered.connect(
            lambda _checked=False: self.cancel_export()
        )

        self.previous_frame_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence("Left"),
            self
        )
        self.previous_frame_shortcut.setContext(
            QtCore.Qt.ShortcutContext.WindowShortcut
        )
        self.previous_frame_shortcut.activated.connect(
            lambda: self.schedule_wheel_move(-1)
        )

        self.next_frame_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence("Right"),
            self
        )
        self.next_frame_shortcut.setContext(
            QtCore.Qt.ShortcutContext.WindowShortcut
        )
        self.next_frame_shortcut.activated.connect(
            lambda: self.schedule_wheel_move(1)
        )

        file_menu = self.menuBar().addMenu("&Fichier")
        file_menu.addAction(
            self.save_project_action
        )
        file_menu.addSeparator()
        file_menu.addAction(
            self.export_project_action
        )
        file_menu.addAction(
            self.queue_export_action
        )

        file_menu.addAction(
            self.cancel_export_action
        )

        main_toolbar = self.addToolBar(
            "Actions principales"
        )
        main_toolbar.setObjectName(
            "main_toolbar"
        )
        main_toolbar.setMovable(False)
        main_toolbar.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        main_toolbar.setIconSize(
            QtCore.QSize(24, 24)
        )

        main_toolbar.addAction(
            self.save_project_action
        )
        main_toolbar.addAction(
            self.export_project_action
        )
        main_toolbar.addAction(
            self.queue_export_action
        )

        main_toolbar.addSeparator()
        main_toolbar.addAction(
            self.cancel_export_action
        )

        for action in (
            self.save_project_action,
            self.export_project_action,
            self.queue_export_action,
            self.cancel_export_action
        ):
            tool_button = main_toolbar.widgetForAction(
                action
            )

            if tool_button is None:
                continue

            tool_button.setToolTip(
                action.toolTip()
            )
            tool_button.setAttribute(
                QtCore.Qt.WidgetAttribute.WA_AlwaysShowToolTips,
                True
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
                self.move_by_frames
            )
            self.shuttle_reader.shuttle_changed.connect(
                self.set_transport_position
            )

        self.refresh_segment_list()

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
        if self.export_status in {"running", "preflight", "confirming"}:
            return

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
        if self.export_status in {"running", "preflight", "confirming"}:
            return

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
        if self.export_status in {"running", "preflight", "confirming"}:
            return

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
        if self.export_status in {"running", "preflight", "confirming"}:
            return

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
        if self.export_status in {"running", "preflight", "confirming"}:
            return

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
        if self.export_status in {"running", "preflight", "confirming"}:
            return

        destination = self.project_path

        if destination is None:
            suggested_path = Path(
                self.source_path
            ).with_suffix(".json")

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
                return None

            destination = selected_path

        return self.write_project(destination)

    def write_project(self, destination):
        try:
            destination = self.trim_project_writer.save(
                self.trim_session,
                destination
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
            return None

        self.project_path = destination
        self.update_window_title()
        self.statusBar().showMessage(
            f"Projet enregistré : {destination}",
            5_000
        )

        return destination

    def export_project(self, queued=False):
        if (
            self.trim_project_exporter.is_running
            or self.audio_preflight_runner.is_running
            or self.pending_export is not None
        ):
            return

        if not self.trim_session.segments:
            QtWidgets.QMessageBox.information(
                self,
                "Montage vide",
                "Ajoute au moins un segment avant "
                "de lancer l’export."
            )
            return

        suggested_output = Path(
            self.source_path
        ).with_suffix(".mkv")

        output_path, _selected_filter = (
            QtWidgets.QFileDialog.getSaveFileName(
                self,
                "Exporter le montage",
                str(suggested_output),
                (
                    "Vidéo Matroska (*.mkv);;"
                    "Tous les fichiers (*)"
                )
            )
        )

        if not output_path:
            return

        project_path = self.project_path

        if project_path is None:
            project_path = Path(
                output_path
            ).with_suffix(".json")

        project_path = self.write_project(
            project_path
        )

        if project_path is None:
            return

        self.pending_export_mode = (
            "queued"
            if queued
            else "immediate"
        )

        self.pending_export = (project_path, output_path)

        try:
            self.audio_preflight_runner.start(project_path)
        except RuntimeError as error:
            self.export_status_changed("failed")
            self.pending_export = None
            self.pending_export_mode = None
            QtWidgets.QMessageBox.warning(
                self,
                "Contrôle audio indisponible",
                str(error)
            )

    def audio_preflight_status_changed(self, status):
        if status == "running":
            self.export_status_changed("preflight")
            return

        if status not in {"succeeded", "failed", "cancelled"}:
            return

        if self.close_after_preflight:
            self.pending_export = None
            self.pending_export_mode = None
            QtCore.QTimer.singleShot(0, self.close)
            return

        if status == "cancelled":
            self.pending_export = None
            self.pending_export_mode = None
            self.export_status_changed("cancelled")
        elif status == "succeeded":
            self.export_status_changed(
                "confirming"
                if self.pending_export is not None
                else "cancelled"
            )

    def audio_preflight_succeeded(self, report):
        if self.audio_preflight_cancel_prompt_active:
            self.deferred_audio_preflight_result = (
                "succeeded",
                report,
            )
            return

        if self.pending_export is None:
            return

        pending_export = self.pending_export

        pending_export_mode = (
            self.pending_export_mode
        )

        status_labels = {
            "signal_detected": "signal détecté",
            "inconclusive": "résultat non concluant",
        }

        lines = []
        for check in report["audio_checks"]:
            source = check["source"]
            index = check["track_index"]
            language = check.get("language") or "non précisée"
            status = check["analysis"]["status"]

            lines.append(
                f"{source}\n"
                f"  Piste {index} — {language} : "
                f"{status_labels.get(status, status)}"
            )

        summary = "\n\n".join(lines)
        if not summary:
            summary = "Aucune piste audio à contrôler."

        answer = QtWidgets.QMessageBox.question(
            self,
            "Contrôle audio avant export",
            (
                f"{summary}\n\n"
                "Ce contrôle mesure la présence d’un signal, "
                "pas la langue réellement parlée.\n"
                "Un résultat non concluant ne prouve pas "
                "que la piste est inutilisable.\n\n"
                "Veux-tu poursuivre l’export avec "
                "les pistes sélectionnées ?"
            ),
            (
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No
            ),
            QtWidgets.QMessageBox.StandardButton.No
        )

        if self.pending_export != pending_export:
            return

        self.pending_export = None
        self.pending_export_mode = None

        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            self.export_status_changed("cancelled")
            return

        project_path, output_path = pending_export

        if pending_export_mode == "queued":
            try:
                self.trim_export_queue_client.enqueue(
                    project_path,
                    output_path,
                )
            except TrimExportQueueError as error:
                self.export_status_changed("failed")
                QtWidgets.QMessageBox.warning(
                    self,
                    "Mise en file impossible",
                    str(error),
                )
                return

            self.export_status_changed("queued")
            QtWidgets.QMessageBox.information(
                self,
                "Montage ajouté à la file",
                (
                    "Le montage sera exporté vers :\n"
                    f"{output_path}"
                ),
            )
            return

        try:
            self.trim_project_exporter.start(
                project_path,
                output_path
            )
        except RuntimeError as error:
            self.export_status_changed("failed")
            QtWidgets.QMessageBox.warning(
                self,
                "Export indisponible",
                str(error)
            )

    def audio_preflight_failed(self, message):
        if self.audio_preflight_cancel_prompt_active:
            self.deferred_audio_preflight_result = (
                "failed",
                message,
            )
            return

        self.pending_export = None
        self.pending_export_mode = None

        if self.close_after_preflight:
            return

        self.export_status_changed("failed")
        QtWidgets.QMessageBox.warning(
            self,
            "Échec du contrôle audio",
            message
        )

    def export_status_changed(self, status):
        self.export_status = status
        running = status in {"running", "preflight", "confirming"}

        self.export_project_action.setEnabled(
            not running
        )
        self.queue_export_action.setEnabled(
            not running
        )
        self.save_project_action.setEnabled(
            not running
        )

        self.cancel_export_action.setEnabled(
            status in {"running", "preflight"}
        )

        self.in_button.setEnabled(
            not running
        )
        self.out_button.setEnabled(
            not running
        )
        self.add_segment_button.setEnabled(
            not running
        )
        self.segment_list.setEnabled(
            not running
        )

        if status in {"preflight", "confirming"}:
            message = (
                "Contrôle audio en cours…"
                if status == "preflight"
                else "Confirmation audio en attente…"
            )
            self.export_elapsed_timer.stop()

            if status in {
                "succeeded",
                "failed",
                "cancelled"
            }:
              self.export_progress_bar.setVisible(True)

            self.export_progress_bar.setRange(0, 0)
            self.export_progress_bar.setFormat(message)
            self.export_progress_bar.setVisible(True)
            self.statusBar().showMessage(message)
            return

        self.export_progress_bar.setRange(0, 100)

        if running:
            self.export_warnings.clear()
            self.export_warning_label.clear()
            self.export_warning_label.setToolTip("")
            self.export_warning_label.setVisible(False)

            self.export_stage = None
            self.export_step = 0
            self.export_total_steps = 0
            self.export_stage_label = ""

            self.export_progress_bar.setRange(
                0,
                100
            )
            self.export_progress_bar.setValue(0)
            self.export_progress_bar.setFormat(
                "Export : préparation…"
            )
            self.export_progress_bar.setVisible(True)

            self.export_elapsed_clock.start()
            self.export_elapsed_timer.start()
            self.update_export_elapsed()
            return

        self.export_elapsed_timer.stop()

        if status == "succeeded":
            self.export_progress_bar.setValue(100)
            self.export_progress_bar.setFormat(
                "Export terminé — %p %"
            )
        elif status == "failed":
            self.export_progress_bar.setFormat(
                "Échec de l’export — %p %"
            )
        elif status == "cancelled":
            self.export_progress_bar.setFormat(
                "Export annulé — %p %"
            )
        elif status == "queued":
            self.export_progress_bar.setValue(0)
            self.export_progress_bar.setFormat(
                "Montage ajouté à la file"
            )
            self.export_progress_bar.setVisible(False)

        messages = {
            "succeeded": "Export terminé",
            "failed": "Échec de l’export",
            "cancelled": "Export annulé",
            "queued": "Montage ajouté à la file"
        }

        message = messages.get(status, status)

        if self.export_elapsed_clock.isValid():
            message = (
                f"{message} — "
                f"{self.format_elapsed_time()}"
            )

        self.statusBar().showMessage(message)

    def export_warning_received(self, event):
        self.export_warnings.append(dict(event))

        count = len(self.export_warnings)
        suffix = "s" if count > 1 else ""

        self.export_warning_label.setText(
            f"⚠ {count} avertissement{suffix}"
        )

        messages = [
            str(item.get("message", "Avertissement d’export"))
            for item in self.export_warnings
        ]

        self.export_warning_label.setToolTip(
            "\n\n".join(messages)
        )
        self.export_warning_label.setVisible(True)

    def export_stage_changed(self, event):
        self.export_stage = event["stage"]
        self.export_step = event["step"]
        self.export_total_steps = event["total"]
        self.export_stage_label = (
            self.export_stage_name(event)
        )

        measurable = self.export_stage in {
            "video",
            "audio"
        }

        self.export_progress_bar.setVisible(
            measurable
        )

        if measurable:
            self.export_progress_bar.setRange(
                0,
                100
            )
            self.export_progress_bar.setValue(0)

        self.update_export_progress_format()
        self.update_export_elapsed()

    def export_stage_name(self, event):
        stage = event["stage"]

        if stage == "video":
            return "Vidéo"

        if stage == "audio":
            roles = {
                "french": "Audio français",
                "original": "Audio original"
            }

            return roles.get(
                event.get("role"),
                "Audio"
            )

        if stage == "subtitles":
            return "Sous-titres"

        if stage == "remux":
            return "Remuxage final"

        return stage

    def export_progress_changed(self, percentage):
        if self.export_stage not in {
            "video",
            "audio"
        }:
            return

        self.export_progress_bar.setValue(
            percentage
        )
        self.update_export_progress_format()

    def update_export_progress_format(self):
        prefix = (
            f"Export : Étape "
            f"{self.export_step}/"
            f"{self.export_total_steps} — "
            f"{self.export_stage_label}"
        )

        if self.export_stage in {
            "video",
            "audio"
        }:
            text = f"{prefix} — %p %"
        else:
            text = f"{prefix}…"

        self.export_progress_bar.setFormat(text)

    def update_export_elapsed(self):
        if self.export_status != "running":
            return

        if self.export_step:
            message = (
                f"Export : Étape "
                f"{self.export_step}/"
                f"{self.export_total_steps} — "
                f"{self.export_stage_label}"
            )

            if self.export_stage not in {
                "video",
                "audio"
            }:
                message = (
                    f"{message} — "
                    "progression non mesurable"
                )

        else:
            message = "Export : préparation"

        self.statusBar().showMessage(
            (
                f"{message} — "
                f"{self.format_elapsed_time()}"
            )
        )

    def format_elapsed_time(self):
        elapsed_seconds = (
            self.export_elapsed_clock.elapsed()
            // 1_000
        )

        hours, remainder = divmod(
            elapsed_seconds,
            3_600
        )
        minutes, seconds = divmod(
            remainder,
            60
        )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    def export_succeeded(self, output_path):
        title = "Export terminé"
        message = (
            "Le fichier a été créé :\n"
            f"{output_path}"
        )

        if self.export_warnings:
            title = "Export terminé avec avertissements"
            message += (
                "\n\nDes avertissements ont été signalés.\n"
                "Consulte leur détail en survolant "
                "la zone d’avertissement de la barre d’état."
            )

        QtWidgets.QMessageBox.information(
            self,
            title,
            message
        )

    def export_failed(self, message):
        self.last_export_error = message

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                prefix="video_encoder_export_error_",
                suffix=".log",
                delete=False
            ) as error_log:
                error_log.write(message)
                log_path = error_log.name

            log_information = (
                "Le diagnostic complet a été conservé dans :\n"
                f"{log_path}"
            )
        except OSError as error:
            log_information = (
                "Le journal n’a pas pu être enregistré :\n"
                f"{error}\n\n"
                "Le diagnostic reste disponible en mémoire "
                "jusqu’à la fermeture de l’application."
            )

        details = message[-6_000:]

        if len(message) > 6_000:
            details = (
                "[Extrait : fin du diagnostic uniquement]\n\n"
                + details
            )

        dialog = QtWidgets.QMessageBox(self)
        dialog.setWindowTitle(
            "Échec de l’export"
        )
        dialog.setIcon(
            QtWidgets.QMessageBox.Icon.Critical
        )
        dialog.setTextFormat(
            QtCore.Qt.TextFormat.PlainText
        )
        dialog.setText(
            "L’export n’a pas abouti."
        )
        dialog.setInformativeText(
            "Le workspace est conservé pour le diagnostic.\n\n"
            + log_information
        )
        dialog.setDetailedText(details)
        dialog.setStandardButtons(
            QtWidgets.QMessageBox.StandardButton.Ok
        )
        dialog.setWindowModality(
            QtCore.Qt.WindowModality.NonModal
        )
        dialog.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_DeleteOnClose,
            True
        )

        self.export_error_dialog = dialog
        dialog.show()
        dialog.raise_()

    def keyPressEvent(self, event):
        if event.isAutoRepeat():
            event.accept()
            return

        editing_keys = {
            QtCore.Qt.Key.Key_I,
            QtCore.Qt.Key.Key_O,
            QtCore.Qt.Key.Key_Return,
            QtCore.Qt.Key.Key_Enter
        }

        if (
            self.trim_project_exporter.is_running
            and event.key() in editing_keys
        ):
            event.accept()
            return

        actions = {
            QtCore.Qt.Key.Key_I: self.set_in_marker,
            QtCore.Qt.Key.Key_O: self.set_out_marker,
            QtCore.Qt.Key.Key_Return: self.add_current_segment,
            QtCore.Qt.Key.Key_Enter: self.add_current_segment,
            QtCore.Qt.Key.Key_J: self.accelerate_backward,
            QtCore.Qt.Key.Key_K: self.pause_transport,
            QtCore.Qt.Key.Key_L: self.accelerate_forward,
            QtCore.Qt.Key.Key_Left: self.show_previous_frame,
            QtCore.Qt.Key.Key_Right: self.show_next_frame,
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
        self.export_elapsed_timer.stop()

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

    def cancel_audio_preflight(self, quitting=False):
        if self.audio_preflight_cancel_prompt_active:
            return False

        if not self.audio_preflight_runner.is_running:
            return True

        if quitting:
            question = (
                "Un contrôle audio est en cours.\n"
                "Veux-tu l’interrompre et quitter ?"
            )
        else:
            question = (
                "Un contrôle audio est en cours.\n"
                "Veux-tu réellement l’interrompre ?"
            )

        self.audio_preflight_cancel_prompt_active = True
        self.deferred_audio_preflight_result = None

        try:
            answer = QtWidgets.QMessageBox.question(
                self,
                "Interrompre le contrôle audio ?",
                question,
                (
                    QtWidgets.QMessageBox.StandardButton.Yes
                    | QtWidgets.QMessageBox.StandardButton.No
                ),
                QtWidgets.QMessageBox.StandardButton.No
            )
        finally:
            self.audio_preflight_cancel_prompt_active = False

        deferred_result = self.deferred_audio_preflight_result
        self.deferred_audio_preflight_result = None

        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            self.pending_export = None
            self.pending_export_mode = None

            if self.audio_preflight_runner.is_running:
                return self.audio_preflight_runner.cancel()

            self.export_status_changed("cancelled")
            return True

        if deferred_result is not None:
            status, payload = deferred_result

            if status == "succeeded":
                self.audio_preflight_succeeded(payload)
            else:
                self.audio_preflight_failed(payload)

        return False

    def cancel_export(self, quitting=False):
        if self.audio_preflight_runner.is_running:
            return self.cancel_audio_preflight(quitting=quitting)
        if not self.trim_project_exporter.is_running:
            return True

        if quitting:
            question = (
                "Un export est toujours en cours.\n"
                "Veux-tu l’interrompre et quitter ?"
            )
        else:
            question = (
                "Un export est toujours en cours.\n"
                "Veux-tu réellement l’interrompre ?"
            )

        answer = QtWidgets.QMessageBox.question(
            self,
            "Interrompre l’export ?",
            question,
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
            return False

        self.statusBar().showMessage(
            "Annulation de l’export…"
        )

        if self.trim_project_exporter.cancel():
            return True

        QtWidgets.QMessageBox.critical(
            self,
            "Annulation impossible",
            (
                "Le processus d’export n’a pas "
                "pu être arrêté."
            )
        )
        return False

    def closeEvent(self, event):
        if self.audio_preflight_runner.is_running:
            event.ignore()

            if self.close_after_preflight:
                return

            if not self.cancel_audio_preflight(quitting=True):
                return

            self.close_after_preflight = True

            if not self.audio_preflight_runner.is_running:
                QtCore.QTimer.singleShot(0, self.close)

            return

        if self.pending_export is not None:
            event.ignore()
            return

        if not self.cancel_export(quitting=True):
            self.close_after_preflight = False
            event.ignore()
            return

        self.shutdown()
        super().closeEvent(event)

    def update_window_title(self):
        title = (
            f"video_encoder — Source active : "
            f"{self.source_path.name}"
        )

        if self.project_path is not None:
            title += (
                f" — Découpage : "
                f"{self.project_path.name}"
            )

        self.setWindowTitle(title)


def select_source_path(arguments):
    if arguments:
        return (
            Path(arguments[0])
            .expanduser()
            .resolve()
        )

    source_path, _selected_filter = (
        QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Ouvrir un enregistrement ou un projet",
            "",
            (
                "Enregistrements et projets "
                "(*.m2t *.mts *.ts *.mkv *.mp4 *.json);;"
                "Projets de montage (*.json);;"
                "Fichiers vidéo "
                "(*.m2t *.mts *.ts *.mkv *.mp4);;"
                "Tous les fichiers (*)"
            )
        )
    )

    if not source_path:
        return None

    return (
        Path(source_path)
        .expanduser()
        .resolve()
    )


def load_startup_selection(
    selected_path,
    reader=None
):
    selected_path = Path(selected_path)

    if selected_path.suffix.lower() != ".json":
        return selected_path, None, None

    reader = reader or TrimProjectFileReader()
    trim_session = reader.load(selected_path)
    sources = trim_session.sources

    if len(sources) != 1:
        raise ValueError(
            "the editor currently supports "
            "single-source projects only"
        )

    source_path = (
        sources[0]
        .path
        .expanduser()
        .resolve()
    )

    return (
        source_path,
        trim_session,
        selected_path
    )

def main():
    if len(sys.argv) > 2:
        print(
            f"Usage: {Path(sys.argv[0]).name} [name] "
            "[media-or-project]",
            file=sys.stderr
        )
        return 2
    app = QtWidgets.QApplication(sys.argv)
    selected_path = select_source_path(
        sys.argv[1:]
    )

    if selected_path is None:
        return 0

    if not selected_path.is_file():
        QtWidgets.QMessageBox.critical(
            None,
            "Fichier introuvable",
            f"Fichier introuvable : {selected_path}"
        )
        return 2

    try:
        (
            source_path,
            trim_session,
            project_path,
        ) = load_startup_selection(
            selected_path
        )
    except (
        KeyError,
        OSError,
        TypeError,
        ValueError,
    ) as error:
        QtWidgets.QMessageBox.critical(
            None,
            "Projet incompatible",
            str(error)
        )
        return 2

    if not source_path.is_file():
        QtWidgets.QMessageBox.critical(
            None,
            "Source introuvable",
            (
                "La source vidéo du projet "
                "est introuvable :\n"
                f"{source_path}"
            )
        )
        return 2

    factory = mlt.Factory()
    factory.init()

    window = MltFrameMonitor(
        source_path,
        trim_session=trim_session,
        project_path=project_path
    )
    window.show()

    if (
        trim_session is not None
        and trim_session.segments
    ):
        initial_frame = (
            trim_session.segments[0].start_frame
        )
    else:
        initial_frame = INITIAL_FRAME

    QtCore.QTimer.singleShot(
        0,
        lambda: window.show_frame(initial_frame)
    )

    try:
        return app.exec()
    finally:
        window.shutdown()
        del window
        factory.close()


if __name__ == "__main__":
    sys.exit(main())
