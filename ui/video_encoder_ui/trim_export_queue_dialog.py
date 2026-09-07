from pathlib import Path

from PySide6 import QtCore, QtWidgets


class TrimExportQueueDialog(QtWidgets.QDialog):
    refresh_requested = QtCore.Signal()
    start_requested = QtCore.Signal()
    retry_requested = QtCore.Signal(object)

    STATUS_LABELS = {
        "queued": "En attente",
        "running": "En cours",
        "done": "Terminé",
        "failed": "Échec",
    }

    HEADERS = (
        "Projet de montage",
        "Fichier de sortie",
        "État",
        "Tentatives",
    )

    def __init__(self, jobs, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "File des montages"
        )
        self.resize(900, 420)

        self.jobs = []
        self.running = False

        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setInterval(5_000)
        self.refresh_timer.timeout.connect(
            self.refresh_requested
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
        header.setSectionResizeMode(
            0,
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            1,
            QtWidgets.QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            2,
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
        )
        header.setSectionResizeMode(
            3,
            QtWidgets.QHeaderView.ResizeMode.ResizeToContents,
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
            "Sélectionne un travail en échec "
            "pour afficher son erreur."
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
        self.jobs = list(jobs)
        self.error_details.clear()
        self.update_start_button()

        self.jobs_table.setRowCount(0)

        for job in self.jobs:
            self.add_job(job)
        self.update_retry_button()

    def set_running(self, running):
        self.running = bool(running)

        if self.running:
            self.refresh_timer.start()
        else:
            self.refresh_timer.stop()

        self.update_start_button()

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
            and job.get("status") == "failed"
        )

    def request_selected_retry(self):
        job = self.selected_job()

        if (
            job is not None
            and job.get("status") == "failed"
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

    # def update_error_details(self):
    #     selected_rows = (
    #         self.jobs_table.selectionModel()
    #         .selectedRows()
    #     )

    #     if not selected_rows:
    #         self.error_details.clear()
    #         return

    #     row = selected_rows[0].row()

    #     if not 0 <= row < len(self.jobs):
    #         self.error_details.clear()
    #         return

    #     error = self.jobs[row].get("error") or ""
    #     self.error_details.setPlainText(error)

    def add_job(self, job):
        row = self.jobs_table.rowCount()
        self.jobs_table.insertRow(row)

        project_path = job.get("input_path") or ""
        output_path = job.get("output_path") or ""
        status = job.get("status") or ""
        attempts = job.get("attempts", 0)

        values = (
            Path(project_path).name,
            output_path,
            self.STATUS_LABELS.get(status, status),
            str(attempts),
        )

        for column, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value)

            if column in (2, 3):
                item.setTextAlignment(
                    QtCore.Qt.AlignmentFlag.AlignCenter
                )

            self.jobs_table.setItem(
                row,
                column,
                item,
            )
