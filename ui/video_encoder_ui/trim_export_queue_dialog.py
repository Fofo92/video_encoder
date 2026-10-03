import time
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from .trim_project_source_names import (
    TrimProjectSourceNames,
)


class TrimExportQueueDialog(QtWidgets.QDialog):
    refresh_requested = QtCore.Signal()
    start_requested = QtCore.Signal()
    retry_requested = QtCore.Signal(object)
    stop_requested = QtCore.Signal()
    finish_current_requested = QtCore.Signal()

    STATUS_LABELS = {
        "queued": "En attente",
        "running": "En cours",
        "done": "Terminé",
        "failed": "Échec",
        "interrupted": "Interrompu",
    }

    HEADERS = (
        "Projet de montage",
        "Source(s)",
        "Fichier de sortie",
        "État",
        "Tentatives",
    )

    def __init__(
        self,
        jobs,
        parent=None,
        source_names=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(
            "File des montages"
        )
        self.resize(900, 420)

        self.jobs = []
        self.running = False
        self.finishing_current = False
        self.progress_event = None
        self.progress_percentage = None
        self.progress_job_id = None
        self.progress_started_at = None
        self.source_names = (
            source_names
            if source_names is not None
            else TrimProjectSourceNames()
        )

        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setInterval(5_000)
        self.refresh_timer.timeout.connect(
            self.refresh_requested
        )

        self.progress_timer = QtCore.QTimer(self)
        self.progress_timer.setInterval(1_000)
        self.progress_timer.timeout.connect(
            self.update_running_progress
        )

        layout = QtWidgets.QVBoxLayout(self)

        self.refresh_status_label = QtWidgets.QLabel(
            "État chargé à l’ouverture",
            self,
        )
        layout.addWidget(
            self.refresh_status_label
        )

        self.jobs_table = QtWidgets.QTableWidget(
            0,
            len(self.HEADERS),
            self,
        )
        self.jobs_table.setHorizontalHeaderLabels(
            self.HEADERS
        )
        self.jobs_table.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.jobs_table.setSelectionBehavior(
            QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.jobs_table.setAlternatingRowColors(True)
        self.jobs_table.verticalHeader().setVisible(False)

        header = self.jobs_table.horizontalHeader()
        header.setMinimumSectionSize(70)

        for column in range(len(self.HEADERS)):
            header.setSectionResizeMode(
                column,
                QtWidgets.QHeaderView.ResizeMode.Interactive,
            )

        for column, width in enumerate(
            (220, 220, 320, 100, 90)
        ):
            header.resizeSection(
                column,
                width,
            )

        error_label = QtWidgets.QLabel(
            "Erreur du travail sélectionné",
            self,
        )
        layout.addWidget(error_label)

        self.error_details = QtWidgets.QPlainTextEdit(
            self
        )
        self.error_details.setReadOnly(True)
        self.error_details.setPlaceholderText(
            "Sélectionne un travail en échec ou "
            "interrompu pour afficher le détail."
        )
        self.error_details.setMaximumHeight(110)
        layout.addWidget(self.error_details)

        self.jobs_table.itemSelectionChanged.connect(
            self.update_error_details
        )
        self.jobs_table.itemSelectionChanged.connect(
            self.update_retry_button
        )
        layout.addWidget(self.jobs_table)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close,
            parent=self,
        )

        self.start_button = buttons.addButton(
            "Lancer la file",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.start_button.clicked.connect(
            self.start_requested
        )

        self.stop_button = buttons.addButton(
            "Interrompre la file",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(
            self.stop_requested
        )

        self.finish_current_button = buttons.addButton(
            "Arrêter après le montage en cours",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.finish_current_button.setEnabled(False)
        self.finish_current_button.clicked.connect(
            self.finish_current_requested
        )

        self.retry_button = buttons.addButton(
            "Relancer le travail",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.retry_button.setEnabled(False)
        self.retry_button.clicked.connect(
            self.request_selected_retry
        )

        self.refresh_button = buttons.addButton(
            "Actualiser",
            QtWidgets.QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.refresh_button.clicked.connect(
            self.refresh_requested
        )

        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.set_jobs(jobs)

    def mark_refreshed(self, time_text):
        self.refresh_status_label.setText(
            f"Dernière actualisation : {time_text}"
        )

    def set_jobs(self, jobs):
        selected_job = self.selected_job()
        selected_job_id = (
            selected_job.get("id")
            if selected_job is not None
            else None
        )
        displayed_error = (
            self.error_details.toPlainText()
        )

        self.jobs = list(jobs)
        self.update_start_button()

        running_job = next(
            (
                job
                for job in self.jobs
                if job.get("status") == "running"
            ),
            None,
        )
        running_job_id = (
            running_job.get("id")
            if running_job is not None
            else None
        )

        if running_job_id != self.progress_job_id:
            self.reset_progress(
                job_id=running_job_id
            )

        table_blocker = QtCore.QSignalBlocker(
            self.jobs_table
        )
        self.jobs_table.setRowCount(0)

        for job in self.jobs:
            self.add_job(job)

        selected_row = (
            next(
                (
                    row
                    for row, job in enumerate(self.jobs)
                    if job.get("id") == selected_job_id
                ),
                None,
            )
            if selected_job_id is not None
            else None
        )

        if selected_row is not None:
            self.jobs_table.selectRow(
                selected_row
            )
        else:
            self.jobs_table.clearSelection()

        del table_blocker

        self.update_retry_button()

        refreshed_job = self.selected_job()
        refreshed_error = (
            refreshed_job.get("error") or ""
            if refreshed_job is not None
            else ""
        )

        if (
            refreshed_job is None
            or refreshed_error != displayed_error
        ):
            self.update_error_details()

    def set_running(self, running):
        self.running = bool(running)

        if not self.running:
            self.finishing_current = False
            self.progress_timer.stop()

        if self.running:
            self.refresh_timer.start()
        else:
            self.refresh_timer.stop()

        self.update_start_button()
        self.update_stop_button()
        self.update_finish_current_button()

    def set_finish_current_requested(self, requested):
        self.finishing_current = bool(requested)
        self.update_finish_current_button()

    def set_progress(self, event):
        if self.progress_started_at is None:
            self.progress_started_at = time.monotonic()
            self.progress_timer.start()

        self.progress_event = dict(event)
        self.progress_percentage = None
        self.update_running_progress()

    def set_percentage(self, percentage):
        self.progress_percentage = percentage
        self.update_running_progress()

    def reset_progress(self, job_id=None):
        self.progress_event = None
        self.progress_percentage = None
        self.progress_job_id = job_id
        self.progress_started_at = None
        self.progress_timer.stop()

    def update_running_progress(self):
        for row, job in enumerate(self.jobs):
            if job.get("status") != "running":
                continue

            item = self.jobs_table.item(row, 3)

            if item is not None:
                item.setText(
                    self.progress_text()
                )
            break

    def progress_text(self):
        event = self.progress_event or {}
        stage = event.get("stage") or "En cours"
        stage_label = {
            "video": "Vidéo",
            "subtitles": "Sous-titres",
            "audio": "Audio",
            "remux": "Remuxage",
        }.get(stage, str(stage))

        if stage == "audio":
            track = event.get("track")
            tracks = event.get("tracks")

            if (
                isinstance(track, int)
                and isinstance(tracks, int)
                and tracks > 1
            ):
                stage_label = (
                    f"{stage_label} "
                    f"{track}/{tracks}"
                )

        parts = [stage_label]

        if self.progress_percentage is not None:
            parts.append(
                f"{self.progress_percentage} %"
            )

        if self.progress_started_at is not None:
            elapsed_seconds = max(
                0,
                int(
                    time.monotonic()
                    - self.progress_started_at
                ),
            )
            parts.append(
                self.format_elapsed_time(
                    elapsed_seconds
                )
            )

        return " — ".join(parts)

    @staticmethod
    def format_elapsed_time(elapsed_seconds):
        hours, remainder = divmod(
            elapsed_seconds,
            3_600,
        )
        minutes, seconds = divmod(
            remainder,
            60,
        )

        if hours:
            return (
                f"{hours:d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return f"{minutes:02d}:{seconds:02d}"

    def update_start_button(self):
        has_queued_jobs = any(
            job.get("status") == "queued"
            for job in self.jobs
        )
        self.start_button.setEnabled(
            has_queued_jobs
            and not self.running
        )
        self.start_button.setText(
            "File en cours…"
            if self.running
            else "Lancer la file"
        )

    def update_stop_button(self):
        self.stop_button.setEnabled(
            self.running
        )

    def update_finish_current_button(self):
        self.finish_current_button.setEnabled(
            self.running
            and not self.finishing_current
        )
        self.finish_current_button.setText(
            "Arrêt demandé…"
            if self.finishing_current
            else "Arrêter après le montage en cours"
        )

    def selected_job(self):
        selected_rows = (
            self.jobs_table.selectionModel()
            .selectedRows()
        )

        if not selected_rows:
            return None

        row = selected_rows[0].row()

        if not 0 <= row < len(self.jobs):
            return None

        return self.jobs[row]

    def update_retry_button(self):
        job = self.selected_job()

        self.retry_button.setEnabled(
            job is not None
            and job.get("status")
            in ("failed", "interrupted")
        )

    def request_selected_retry(self):
        job = self.selected_job()

        if (
            job is not None
            and job.get("status")
            in ("failed", "interrupted")
        ):
            self.retry_requested.emit(job)

    def update_error_details(self):
        job = self.selected_job()

        if job is None:
            self.error_details.clear()
            return

        self.error_details.setPlainText(
            job.get("error") or ""
        )

    def add_job(self, job):
        row = self.jobs_table.rowCount()
        self.jobs_table.insertRow(row)

        project_path = job.get("input_path") or ""
        output_path = job.get("output_path") or ""
        status = job.get("status") or ""
        attempts = job.get("attempts", 0)

        status_text = self.STATUS_LABELS.get(
            status,
            status,
        )

        if (
            status == "running"
            and self.progress_event is not None
        ):
            status_text = self.progress_text()

        values = (
            Path(project_path).name,
            self.source_names(project_path),
            output_path,
            status_text,
            str(attempts),
        )

        for column, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value)

            if column in (3, 4):
                item.setTextAlignment(
                    QtCore.Qt.AlignmentFlag.AlignCenter
                )

            self.jobs_table.setItem(
                row,
                column,
                item,
            )
