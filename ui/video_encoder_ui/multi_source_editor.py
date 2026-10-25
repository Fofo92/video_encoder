from fractions import Fraction
from pathlib import Path
import uuid

from PySide6 import QtCore, QtGui, QtWidgets

from .mlt_frame_source import MltFrameSource
from .mlt_audio_player import MltAudioPlayer
from .trim_session import SourceReference


class MultiSourceEditor:
    """Source selection changes the preview, never the assembled timeline."""

    @staticmethod
    def cadence(preview):
        return Fraction(preview.frame_rate_numerator, preview.frame_rate_denominator)

    def open_source_preview(self, path):
        return MltFrameSource(path, preview_width=self.frame_source.preview_width,
                              preview_height=self.frame_source.preview_height)

    def validate_source_cadences(self):
        if len(self.trim_session.sources) < 2:
            return
        expected = self.cadence(self.frame_source)
        for source in self.trim_session.sources:
            if source.identifier == self.source_id:
                continue
            if not source.path.is_file():
                raise ValueError(f"Source introuvable : {source.path}")
            preview = self.open_source_preview(source.path)
            try:
                if self.cadence(preview) != expected:
                    raise ValueError("Ce premier parcours multi-source exige la même cadence d’images : "
                                     f"{source.path.name}")
            finally:
                preview.close()

    def setup_source_controls(self):
        self.source_positions = {}
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Source affichée :"))
        self.source_selector = QtWidgets.QComboBox()
        self.source_selector.setMinimumContentsLength(30)
        self.source_selector.setSizeAdjustPolicy(QtWidgets.QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        row.addWidget(self.source_selector, stretch=1)
        self.centralWidget().layout().insertLayout(0, row)
        self.source_selector.currentIndexChanged.connect(self.source_selected)

        self.add_source_action = QtGui.QAction("Ajouter une source au montage…", self)
        self.add_source_action.setShortcut(QtGui.QKeySequence("Ctrl+Shift+O"))
        self.add_source_action.triggered.connect(self.add_montage_source)
        for action in self.menuBar().actions():
            if action.text().replace("&", "") == "Sources":
                action.menu().addAction(self.add_source_action)

        self.move_segment_up_action = QtGui.QAction("Monter le segment sélectionné", self)
        self.move_segment_down_action = QtGui.QAction("Descendre le segment sélectionné", self)
        self.move_segment_up_action.setShortcut(QtGui.QKeySequence("Alt+Up"))
        self.move_segment_down_action.setShortcut(QtGui.QKeySequence("Alt+Down"))
        self.move_segment_up_action.triggered.connect(lambda: self.move_selected_segment(-1))
        self.move_segment_down_action.triggered.connect(lambda: self.move_selected_segment(1))
        for action in self.menuBar().actions():
            if action.text().replace("&", "") == "Montage":
                action.menu().addSeparator()
                action.menu().addAction(self.move_segment_up_action)
                action.menu().addAction(self.move_segment_down_action)
        self.segment_list.itemSelectionChanged.connect(self.update_source_controls)
        self.refresh_source_selector()
        self.update_source_controls()

    def refresh_source_selector(self):
        blocker = QtCore.QSignalBlocker(self.source_selector)
        self.source_selector.clear()
        for source in self.trim_session.sources:
            self.source_selector.addItem(f"{source.identifier} — {source.path.name}", source.identifier)
            self.source_selector.setItemData(self.source_selector.count() - 1, str(source.path),
                                             QtCore.Qt.ItemDataRole.ToolTipRole)
        self.source_selector.setCurrentIndex(self.source_selector.findData(self.source_id))
        del blocker

    def update_source_controls(self):
        if not hasattr(self, "source_selector"):
            return
        enabled = self.export_status not in {"running", "preflight", "confirming"}
        self.source_selector.setEnabled(enabled)
        self.add_source_action.setEnabled(enabled)
        row = self.segment_list.currentRow()
        self.move_segment_up_action.setEnabled(enabled and row > 0)
        self.move_segment_down_action.setEnabled(enabled and 0 <= row < len(self.trim_session.segments) - 1)

    def source_selected(self, index):
        if index < 0:
            return
        identifier = self.source_selector.itemData(index)
        if not self.activate_source(identifier):
            self.refresh_source_selector()

    def confirm_source_switch(self):
        if self.in_position is None and self.out_position is None:
            return True
        return QtWidgets.QMessageBox.question(
            self, "Changer de source", "Changer de source réinitialisera les repères IN/OUT affichés.\n"
            "Les segments déjà ajoutés au montage sont conservés. Continuer ?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No) == QtWidgets.QMessageBox.StandardButton.Yes

    def activate_source(self, identifier):
        if identifier == self.source_id:
            return True
        if self.export_status in {"running", "preflight", "confirming"}:
            return False
        source = next((item for item in self.trim_session.sources if item.identifier == identifier), None)
        if source is None or not self.confirm_source_switch():
            return False
        preview = audio = None
        try:
            if not source.path.is_file():
                raise ValueError(f"Source introuvable : {source.path}")
            preview = self.open_source_preview(source.path)
            if self.cadence(preview) != self.cadence(self.frame_source):
                raise ValueError("Les sources doivent avoir la même cadence d’images.")
            audio = MltAudioPlayer(source.path)
        except (OSError, ValueError, RuntimeError) as error:
            if preview is not None:
                preview.close()
            if audio is not None:
                audio.close()
            QtWidgets.QMessageBox.warning(self, "Source non ouverte", str(error))
            return False

        self.set_transport_position(0)
        self.scrub_timer.stop()
        self.wheel_timer.stop()
        self.source_positions[self.source_id] = self.current_position
        self.audio_player.close()
        self.frame_source.close()
        self.frame_source, self.audio_player = preview, audio
        self.source_id, self.source_path = source.identifier, source.path
        self.frames_per_second = preview.frames_per_second
        position = min(self.source_positions.get(identifier, 0), preview.length - 1)
        self.pending_position = self.pending_wheel_position = position
        self.previous_wheel_event_timestamp = None
        self.horizontal_wheel_remainder = self.vertical_wheel_remainder = 0
        self.position_slider.setRange(0, preview.length - 1)
        self.clear_active_markers()
        self.refresh_source_selector()
        self.refresh_segment_list()
        self.show_frame(position)
        self.update_window_title()
        return True

    def add_montage_source(self):
        if self.export_status in {"running", "preflight", "confirming"}:
            return
        selected, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Ajouter une source au montage", str(self.source_path.parent),
            "Fichiers vidéo (*.m2t *.mts *.ts *.mkv *.mp4 *.m4v);;Tous les fichiers (*)")
        if not selected:
            return
        path = Path(selected).expanduser().resolve()
        existing = next((source for source in self.trim_session.sources if source.path.resolve() == path), None)
        if existing:
            self.activate_source(existing.identifier)
            return
        preview = None
        try:
            if not path.is_file():
                raise ValueError(f"Source introuvable : {path}")
            preview = self.open_source_preview(path)
            if self.cadence(preview) != self.cadence(self.frame_source):
                raise ValueError("Ce premier parcours multi-source exige la même cadence d’images.")
        except (OSError, ValueError, RuntimeError) as error:
            QtWidgets.QMessageBox.warning(self, "Source non ajoutée", str(error))
            return
        finally:
            if preview is not None:
                preview.close()
        source = SourceReference(identifier=f"source-{uuid.uuid4().hex[:8]}", path=path)
        self.trim_session.add_source(source)
        self.set_project_modified()
        self.refresh_source_selector()
        self.refresh_segment_list()
        self.activate_source(source.identifier)

    def move_selected_segment(self, offset):
        if self.export_status in {"running", "preflight", "confirming"}:
            return
        index = self.segment_list.currentRow()
        target = index + offset
        if not 0 <= index < len(self.trim_session.segments) or not 0 <= target < len(self.trim_session.segments):
            return
        try:
            self.trim_session.move_segment(index, target)
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, "Ordre non modifié", str(error))
            return
        self.clear_active_markers()
        self.set_project_modified()
        self.refresh_segment_list()
        self.segment_list.selectRow(target)
        self.update_source_controls()
