from pathlib import Path

from PySide6 import QtCore, QtWidgets

from .trim_export_queue_client import TrimExportQueueError


class ProjectTrashDialog(QtWidgets.QDialog):
    def __init__(self, parent, client):
        super().__init__(parent)
        self.client = client
        self.entries = []
        self.errors = []
        self.setWindowTitle("Corbeille des projets")
        self.resize(960, 450)
        layout = QtWidgets.QVBoxLayout(self)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Projet", "Date de suppression", "Taille", "Emplacement d’origine"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        self.warning = QtWidgets.QLabel()
        self.warning.setWordWrap(True)
        layout.addWidget(self.warning)
        self.summary = QtWidgets.QLabel()
        layout.addWidget(self.summary)
        row = QtWidgets.QHBoxLayout()
        self.restore_button = QtWidgets.QPushButton("Restaurer la sélection")
        self.purge_button = QtWidgets.QPushButton("Supprimer définitivement la sélection…")
        self.empty_button = QtWidgets.QPushButton("Vider la corbeille…")
        self.refresh_button = QtWidgets.QPushButton("Actualiser")
        self.add_button = QtWidgets.QPushButton("Ajouter un dossier…")
        for button in (self.restore_button, self.purge_button, self.empty_button,
                       self.refresh_button, self.add_button):
            button.setAutoDefault(False)
            row.addWidget(button)
        layout.addLayout(row)
        close = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject)
        layout.addWidget(close)
        self.restore_button.clicked.connect(lambda: self.apply("restore", self.selected_entries()))
        self.purge_button.clicked.connect(lambda: self.apply("purge", self.selected_entries()))
        self.empty_button.clicked.connect(lambda: self.apply("purge", self.entries))
        self.refresh_button.clicked.connect(self.refresh)
        self.add_button.clicked.connect(self.add_root)
        self.table.itemSelectionChanged.connect(self.update_buttons)
        self.refresh()

    @staticmethod
    def size_label(value):
        return f"{value / (1024 ** 3):.2f} Gio" if value >= 1024 ** 3 else f"{value / (1024 ** 2):.1f} Mio"

    def refresh(self):
        try:
            document = self.client.project_trash()
        except TrimExportQueueError as error:
            self.entries = []
            self.errors = [str(error)]
        else:
            self.entries = document['entries']
            self.errors = document['errors']
        self.table.setRowCount(len(self.entries))
        for row, entry in enumerate(self.entries):
            path = entry.get('project') or entry['files'][0]
            values = (Path(path).name, entry['deleted_at'], self.size_label(entry['bytes']), str(Path(path).parent))
            for column, value in enumerate(values):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem(value))
        self.warning.setText("\n".join(self.errors))
        self.warning.setVisible(bool(self.errors))
        total = sum(entry['bytes'] for entry in self.entries)
        self.summary.setText(f"{len(self.entries)} projet(s) — {self.size_label(total)} — conservation sans limite de durée")
        self.update_buttons()

    def selected_entries(self):
        rows = sorted({index.row() for index in self.table.selectionModel().selectedRows()})
        return [self.entries[row] for row in rows]

    def update_buttons(self):
        selected = bool(self.selected_entries())
        self.restore_button.setEnabled(selected)
        self.purge_button.setEnabled(selected)
        self.empty_button.setEnabled(bool(self.entries) and not self.errors)

    def add_root(self):
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Dossier contenant une corbeille de projets")
        if not path:
            return
        root = Path(path)
        if root.name != '.video_encoder_trash':
            root = root / '.video_encoder_trash'
        try:
            self.client.project_trash("register", str(root))
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(self, "Corbeille inaccessible", str(error))
        self.refresh()

    def apply(self, operation, entries):
        entries = list(entries)
        if not entries:
            return
        total = self.size_label(sum(entry['bytes'] for entry in entries))
        names = "\n".join(entry.get('project') or entry['directory'] for entry in entries)
        verb = "Restaurer sans écraser de fichier existant" if operation == "restore" else "Supprimer définitivement, sans récupération"
        answer = QtWidgets.QMessageBox.question(
            self, "Confirmer la restauration" if operation == "restore" else "Confirmer la suppression définitive",
            f"{verb} : {len(entries)} projet(s), {total} ?\n\n{names}",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        failures = []
        completed = 0
        for entry in entries:
            try:
                self.client.project_trash(operation, entry['directory'], entry['token'])
                completed += 1
            except TrimExportQueueError as error:
                failures.append(f"{entry['directory']} : {error}")
        self.refresh()
        if failures:
            QtWidgets.QMessageBox.warning(self, "Opération partielle",
                                         f"{completed} projet(s) traité(s).\n\n" + "\n".join(failures))
