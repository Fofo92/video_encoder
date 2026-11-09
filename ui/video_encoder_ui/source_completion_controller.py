import uuid

from PySide6 import QtCore, QtWidgets

from .source_completion_plan import SourceCompletionError, SourceCompletionPlan
from .source_quarantine_client import SourceQuarantineError
from .source_quarantine_dialogs import report_quarantine_batch
from .trim_export_queue_client import TrimExportQueueError


class SourceCompletionController(QtCore.QObject):
    """Only an explicit human confirmation closes a source, never an empty queue."""

    def __init__(self, parent, queue_client, quarantine_client, plan=None):
        super().__init__(parent)
        self.parent_window = parent
        self.queue_client = queue_client
        self.quarantine_client = quarantine_client
        self.plan = plan or SourceCompletionPlan()
        self.known_done = {}
        self.pending_ids = set()
        self.reviewed_sources = {}
        self.direct_jobs = []
        self.dialog = None
        self.case = None
        self.reporting_error = False
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(10_000)
        self.timer.timeout.connect(self.poll)

    def start(self):
        try:
            self.known_done = self.completed_keys(self.queue_client.list_jobs())
        except TrimExportQueueError:
            pass
        self.timer.start()

    @staticmethod
    def completed_keys(jobs):
        return {job["id"]: (job.get("finished_at"), job.get("output_path"))
                for job in jobs if job.get("status") == "done"}

    def jobs(self):
        return self.queue_client.list_jobs() + self.direct_jobs

    def poll(self, inspect_all=False):
        if self.dialog is not None or self.reporting_error:
            return
        try:
            jobs = self.jobs()
            done = self.completed_keys(jobs)
            self.pending_ids.update(key for key, value in done.items() if self.known_done.get(key) != value)
            self.known_done = done
            cases = self.plan.collect(jobs)
            if inspect_all and len(cases) > 1:
                self.show_batch_confirmation(cases)
                return
            for case in cases:
                if inspect_all or self.needs_confirmation(case):
                    self.show_confirmation(case)
                    return
            if inspect_all:
                QtWidgets.QMessageBox.information(self.parent_window, "Sources encodées",
                    "Aucune source à confirmer. Les sources encore utilisées, introuvables ou dont une sortie "
                    "manque sont conservées.")
        except (TrimExportQueueError, SourceCompletionError) as error:
            if inspect_all:
                QtWidgets.QMessageBox.warning(self.parent_window, "Sources conservées", str(error))

    def needs_confirmation(self, case):
        completed = self.completed_keys(case.jobs)
        return (any(job_id in self.pending_ids for job_id in completed)
                and self.reviewed_sources.get(case.source) != completed)

    def record_export(self, project_path, output_path):
        if project_path is None:
            return
        self.direct_jobs.append({"id": str(uuid.uuid4()), "kind": "trim_export", "status": "done",
                                 "input_path": str(project_path), "output_path": str(output_path)})
        QtCore.QTimer.singleShot(0, self.poll)

    def install_menu_bar(self, menu_bar):
        for action in menu_bar.actions():
            if action.text().replace("&", "") == "Sources" and action.menu() is not None:
                item = action.menu().addAction("Vérifier les sources avant quarantaine…")
                item.triggered.connect(lambda checked=False: self.poll(inspect_all=True))
                return

    def show_confirmation(self, case):
        self.case = case
        dialog = QtWidgets.QDialog(self.parent_window)
        self.dialog = dialog
        dialog.setWindowTitle("Tous les programmes de cette source sont-ils encodés ?")
        dialog.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel("La file ne peut pas savoir s’il reste un autre programme à préparer.\n\n"
                                f"Source : {case.source}\n\n"
                                "Confirme uniquement si tous les programmes utiles ont été encodés.")
        label.setWordWrap(True)
        layout.addWidget(label)
        outputs = QtWidgets.QPlainTextEdit()
        outputs.setReadOnly(True)
        outputs.setPlainText("Sorties présentes :\n" + "\n".join(path for path, _identity in case.outputs))
        layout.addWidget(outputs)
        keep = QtWidgets.QPushButton("Il reste un programme ou un doute : conserver la source")
        keep.setDefault(True)
        keep.clicked.connect(dialog.reject)
        layout.addWidget(keep)
        close_source = QtWidgets.QPushButton("Tout est encodé : mettre la source en quarantaine")
        close_source.setAutoDefault(False)
        close_source.clicked.connect(self.confirm)
        layout.addWidget(close_source)
        dialog.finished.connect(self.closed)
        dialog.resize(650, 300)
        dialog.show()

    def show_batch_confirmation(self, cases):
        dialog = QtWidgets.QDialog(self.parent_window)
        self.dialog = dialog
        dialog.setWindowTitle("Vérifier les sources avant quarantaine")
        layout = QtWidgets.QVBoxLayout(dialog)
        label = QtWidgets.QLabel(
            "Décoche les sources qu’il faut conserver. Confirme uniquement si tous les programmes "
            "utiles des sources cochées ont été encodés."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        tree = QtWidgets.QTreeWidget()
        tree.setHeaderLabel("Sources et sorties présentes")
        layout.addWidget(tree)
        rows = []
        for case in sorted(cases, key=lambda item: item.source):
            row = QtWidgets.QTreeWidgetItem(tree, [str(case.source)])
            for path, _identity in case.outputs:
                QtWidgets.QTreeWidgetItem(row, [str(path)])
            row.setCheckState(0, QtCore.Qt.CheckState.Checked)
            row.setExpanded(True)
            rows.append((case, row))
        tree.header().setStretchLastSection(False)
        tree.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        keep = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        keep.setText("Conserver toutes les sources")
        keep.setDefault(True)
        buttons.rejected.connect(dialog.reject)
        move = buttons.addButton("", QtWidgets.QDialogButtonBox.ButtonRole.ActionRole)
        move.setAutoDefault(False)
        layout.addWidget(buttons)

        def selected_cases():
            return [case for case, row in rows if row.checkState(0) == QtCore.Qt.CheckState.Checked]

        def update_button():
            count = len(selected_cases())
            move.setEnabled(count > 0)
            move.setText(f"Mettre en quarantaine les sources cochées ({count})")

        tree.itemChanged.connect(update_button)
        move.clicked.connect(lambda: self.confirm_batch(selected_cases()))
        dialog.finished.connect(lambda result: self.close_review(cases))
        update_button()
        dialog.resize(800, 420)
        dialog.show()

    def confirm_batch(self, cases):
        moved, failed = [], []
        self.reporting_error = True
        try:
            for case in cases:
                try:
                    self.quarantine_case(case)
                except (SourceCompletionError, SourceQuarantineError, TrimExportQueueError, OSError) as error:
                    failed.append((case.source, str(error)))
                else:
                    moved.append(case.source)
            self.dialog.accept()
            report_quarantine_batch(self.parent_window, moved, failed)
        finally:
            self.reporting_error = False

    def quarantine_case(self, case):
        self.plan.validate(case, self.jobs())
        self.quarantine_client.quarantine(case.source)

    def confirm(self):
        if self.case is None or self.reporting_error:
            return
        try:
            self.quarantine_case(self.case)
        except (SourceCompletionError, SourceQuarantineError, TrimExportQueueError, OSError) as error:
            self.reporting_error = True
            try:
                self.dialog.reject()
                QtWidgets.QMessageBox.warning(
                    self.parent_window, "Source conservée",
                    f"{error}\n\nLa confirmation a été fermée. Pour réexaminer la situation, "
                    "utilise Sources → Vérifier les sources avant quarantaine…")
            finally:
                self.reporting_error = False
            return
        self.dialog.accept()

    def closed(self, _result):
        self.close_review([self.case])

    def close_review(self, cases):
        # One completed job can reference several sources. A decision concerns
        # only this source, never the other sources of those same jobs.
        for case in cases:
            self.reviewed_sources[case.source] = self.completed_keys(case.jobs)
        dialog = self.dialog
        self.dialog = None
        self.case = None
        dialog.deleteLater()
        QtCore.QTimer.singleShot(0, self.poll)

