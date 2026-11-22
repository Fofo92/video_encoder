import json
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .quarantine_forecast import quarantine_forecast
from .trim_export_queue_client import TrimExportQueueClient, TrimExportQueueError


def absent_capture_rows(root, entries):
    if not root:
        return set()
    root = Path(root)
    try:
        present = set(root.iterdir())
    except OSError:
        return set()
    return {
        row for row, entry in enumerate(entries)
        if entry["state"] == "blocked"
        and (path := Path(entry["path"])).parent == root and path not in present
    }


class QuarantinePolicyClient:
    def __init__(self, queue=None):
        self.queue = queue or TrimExportQueueClient()

    def request(self, operation="list", *arguments):
        output = self.queue.manage("quarantine", operation, *arguments)
        try:
            result = json.loads(output)
            if (not isinstance(result, dict) or result.get("format") != "video_encoder.quarantine"
                    or result.get("version") != 1 or not isinstance(result.get("entries"), list)
                    or not isinstance(result.get("errors"), list)):
                raise ValueError("Format inattendu")
            return result
        except (ValueError, TypeError) as error:
            raise TrimExportQueueError("Réponse du suivi de quarantaine invalide.") from error


class QuarantinePolicyDialog(QtWidgets.QDialog):
    STATE_NAMES = {
        "untracked": "Sans date", "scheduled": "Programmée", "due": "Échue",
        "blocked": "Conservée", "absent": "Absente",
    }

    def __init__(self, parent=None, client=None):
        super().__init__(parent)
        self.client = client or QuarantinePolicyClient()
        self.entries = []
        self.absent_rows = set()
        self.setWindowTitle("Quarantaine — échéances de suppression")
        self.resize(1100, 480)
        layout = QtWidgets.QVBoxLayout(self)
        description = QtWidgets.QLabel(
            "Conservation : 30 jours. Suppression automatique uniquement si tous les projets et leurs "
            "encodages sont vérifiés et qu’aucune tâche ne dépend de la source. "
            "Pour les anciens fichiers vérifiés, le prochain contrôle démarre un délai neuf de 30 jours.")
        description.setWordWrap(True)
        layout.addWidget(description)
        self.timer_label = QtWidgets.QLabel(self.timer_status())
        layout.addWidget(self.timer_label)
        self.hide_absent = QtWidgets.QCheckBox("Masquer les captures absentes")
        self.hide_absent.setChecked(True)
        self.hide_absent.toggled.connect(self.apply_absent_filter)
        filters = QtWidgets.QHBoxLayout()
        self.source_search = QtWidgets.QLineEdit()
        self.source_search.setPlaceholderText("Rechercher un titre de source")
        self.source_search.setAccessibleName("Titre de source")
        self.source_search.setClearButtonEnabled(True)
        filters.addWidget(self.source_search, 1)
        self.state_filter = QtWidgets.QComboBox()
        self.state_filter.setAccessibleName("État de la capture")
        self.state_filter.addItem("Tous les états")
        for state, label in self.STATE_NAMES.items():
            self.state_filter.addItem(label, state)
        filters.addWidget(self.state_filter)
        filters.addWidget(self.hide_absent)
        self.copy_button = QtWidgets.QPushButton("Copier le nom")
        self.copy_button.setAutoDefault(False)
        filters.addWidget(self.copy_button)
        layout.addLayout(filters)
        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Source", "Entrée / suivi", "Suppression à partir du", "État", "Motif"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        self.message = QtWidgets.QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        buttons = QtWidgets.QHBoxLayout()
        self.enroll_button = QtWidgets.QPushButton("Activer le suivi de la sélection (30 jours)")
        self.preview_button = QtWidgets.QPushButton("Aperçu des suppressions échues")
        forecast_button = QtWidgets.QPushButton("Échéancier estimatif…")
        self.refresh_button = QtWidgets.QPushButton("Actualiser")
        self.associate_button = QtWidgets.QPushButton("Associer un projet…")
        for button in (self.enroll_button, self.associate_button, self.preview_button, forecast_button,
                       self.refresh_button):
            button.setAutoDefault(False)
            buttons.addWidget(button)
        layout.addLayout(buttons)
        close = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self.refresh_button.clicked.connect(self.refresh)
        self.preview_button.clicked.connect(self.preview)
        forecast_button.clicked.connect(self.show_forecast)
        self.enroll_button.clicked.connect(self.enroll)
        self.associate_button.clicked.connect(self.associate_project)
        self.table.itemSelectionChanged.connect(self.update_buttons)
        self.source_search.textChanged.connect(self.apply_absent_filter)
        self.state_filter.currentIndexChanged.connect(self.apply_absent_filter)
        self.copy_button.clicked.connect(self.copy_source_name)
        self.copy_shortcut = QtGui.QShortcut(QtGui.QKeySequence.StandardKey.Copy, self.table)
        self.copy_shortcut.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self.copy_shortcut.activated.connect(self.copy_source_name)
        self.refresh()

    @staticmethod
    def timer_status():
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "video-encoder-quarantine.timer"],
                text=True, capture_output=True, check=False, timeout=3)
            return ("Suppression automatique : minuteur actif" if result.stdout.strip() == "active"
                    else "Suppression automatique : minuteur inactif (aucune purge planifiée par ce minuteur)")
        except (OSError, subprocess.TimeoutExpired):
            return "Suppression automatique : état du minuteur indisponible"

    @staticmethod
    def date_label(value):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%d/%m/%Y %H:%M") if value else "—"

    def refresh(self):
        self.timer_label.setText(self.timer_status())
        try:
            result = self.client.request()
            self.entries = result["entries"]
            self.absent_rows = absent_capture_rows(result.get("root"), self.entries)
            self.message.setText("\n".join(result["errors"]))
        except (TrimExportQueueError, OSError) as error:
            self.entries = []
            self.absent_rows = set()
            self.message.setText(str(error))
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            state_key = self.state_for(row)
            state = self.STATE_NAMES.get(state_key, state_key)
            values = (Path(entry["path"]).name, self.date_label(entry.get("entered_at")),
                      self.date_label(entry.get("delete_after")), state,
                      entry.get("reason", ""))
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                item.setToolTip(value if column == 4 else entry["path"])
                self.table.setItem(row, column, item)
        self.apply_absent_filter()
        self.update_buttons()

    def apply_absent_filter(self):
        self.hide_absent.setText(f"Masquer les captures absentes ({len(self.absent_rows)})")
        state_filter = self.state_filter.currentData()
        hide_absent = self.hide_absent.isChecked() and state_filter != "absent"
        query = self.source_search.text().strip().casefold()
        for row, entry in enumerate(self.entries):
            state = self.state_for(row)
            name = Path(entry["path"]).name.casefold()
            hidden = ((hide_absent and state == "absent")
                      or (state_filter is not None and state != state_filter)
                      or query not in name)
            self.table.setRowHidden(row, hidden)
        self.update_buttons()

    def state_for(self, row):
        return "absent" if row in self.absent_rows else self.entries[row]["state"]

    def selected_source_row(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows or self.table.isRowHidden(rows[0].row()):
            return None
        return rows[0].row()

    def copy_source_name(self):
        row = self.selected_source_row()
        if row is not None:
            QtWidgets.QApplication.clipboard().setText(Path(self.entries[row]["path"]).name)

    def update_buttons(self):
        row = self.selected_source_row()
        self.copy_button.setEnabled(row is not None)
        self.enroll_button.setEnabled(row is not None and self.entries[row]["state"] == "untracked")
        self.associate_button.setEnabled(self.enroll_button.isEnabled())

    def associate_project(self):
        row = self.selected_source_row()
        if row is None or self.entries[row]["state"] != "untracked":
            return
        project, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Projet de cette capture", "/videos", "Projets (*.json)")
        if not project:
            return
        try:
            self.client.request("enroll", self.entries[row]["path"], "--project", project)
        except (TrimExportQueueError, OSError) as error:
            QtWidgets.QMessageBox.warning(self, "Source conservée — vérification nécessaire", str(error))
        self.refresh()

    def enroll(self):
        row = self.selected_source_row()
        if row is None or self.entries[row]["state"] != "untracked":
            return
        try:
            self.client.request("enroll", self.entries[row]["path"])
        except (TrimExportQueueError, OSError) as error:
            QtWidgets.QMessageBox.warning(self, "Source conservée — vérification nécessaire", str(error))
        self.refresh()

    def preview(self):
        self.refresh()
        due = [entry["path"] for entry in self.entries if entry["state"] == "due"]
        QtWidgets.QMessageBox.information(
            self, "Aperçu — aucune suppression effectuée",
            "\n".join(due) if due else "Aucune suppression éligible à cet instant.")

    def show_forecast(self):
        try:
            report = self.client.request()
            if report["errors"]:
                raise ValueError("\n".join(report["errors"]))
            if not report.get("root"):
                raise ValueError("Le dossier de quarantaine est absent de la réponse. Mets à jour video_encoder.")
            total, disk, rows = quarantine_forecast(report, datetime.now())
        except (TrimExportQueueError, OSError, ValueError) as error:
            QtWidgets.QMessageBox.warning(self, "Échéancier indisponible", str(error))
            return

        def go(size):
            return f"{size / 1e9:.1f}".replace(".", ",") + " Go"

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Échéancier estimatif de la quarantaine")
        layout = QtWidgets.QVBoxLayout(dialog)
        layout.addWidget(QtWidgets.QLabel(
            f"Disque de la quarantaine : {go(disk.total)} · Libre : {go(disk.free)} · Quarantaine : {go(total)}"
        ))
        note = QtWidgets.QLabel(
            self.timer_status() + "\n"
            "Projection après le passage quotidien de 03 h 30, si les contrôles restent valides et sans nouvel ajout. "
            "Les captures sans échéance ou bloquées restent dans le volume projeté. "
            "Le gain sur le disque dépend des blocs réellement libérés."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        if rows:
            table = QtWidgets.QTableWidget(len(rows), 5)
            table.setHorizontalHeaderLabels(
                ["Date", "Captures", "Volume supprimable", "Quarantaine restante", "Libre estimé sur le disque"]
            )
            table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
            table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
            for row, (date, count, removed, remaining, free) in enumerate(rows):
                for column, value in enumerate((date.strftime("%d/%m/%Y"), str(count), go(removed),
                                                go(remaining), go(free))):
                    table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
            layout.addWidget(table)
        else:
            layout.addWidget(QtWidgets.QLabel("Aucune suppression prévisible avec les échéances actuelles."))
        close = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(dialog.reject)
        layout.addWidget(close)
        dialog.resize(950, 460)
        dialog.exec()
        dialog.deleteLater()


def show_quarantine_policy(parent):
    QuarantinePolicyDialog(parent).exec()
