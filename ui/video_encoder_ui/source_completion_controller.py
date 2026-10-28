import uuid

from PySide6 import QtCore, QtWidgets

from .source_completion_plan import SourceCompletionError, SourceCompletionPlan
from .source_quarantine_client import SourceQuarantineError
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
        if self.dialog is not None:
            return
        try:
            jobs = self.jobs()
            done = self.completed_keys(jobs)
            self.pending_ids.update(key for key, value in done.items() if self.known_done.get(key) != value)
            self.known_done = done
            cases = self.plan.collect(jobs)
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
                item = action.menu().addAction("Examiner les sources encodées…")
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

    def confirm(self):
        if self.case is None:
            return
        try:
            self.plan.validate(self.case, self.jobs())
            self.quarantine_client.quarantine(self.case.source)
        except (SourceCompletionError, SourceQuarantineError, TrimExportQueueError, OSError) as error:
            QtWidgets.QMessageBox.warning(self.dialog, "Source conservée", str(error))
            return
        self.dialog.accept()

    def closed(self, _result):
        # One completed job can reference several sources. A decision concerns
        # only this source, never the other sources of those same jobs.
        self.reviewed_sources[self.case.source] = self.completed_keys(self.case.jobs)
        dialog = self.dialog
        self.dialog = None
        self.case = None
        dialog.deleteLater()
        QtCore.QTimer.singleShot(0, self.poll)
