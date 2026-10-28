from concurrent.futures import ThreadPoolExecutor
import time

from PySide6 import QtCore, QtWidgets

from .vidb_modal_browser import build_vidb_browser, size_vidb_dialog, trace_vidb
from .vidb_review_completion import watch_completion


class VidbExportReview(QtWidgets.QDialog):
    """Keep the export in progress while the browser confirms its identity."""

    def __init__(self, parent, result, refresh):
        super().__init__(parent)
        trace_vidb("export review opened; initial status=" + str(result.get("status")))
        self.result_data = result
        self.wait_for_change = result.get("status") == "identified"
        self.confirmed_record_id = None
        self.refresh = refresh
        self.future = None
        self.next_refresh = 0
        self.closed = False
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="vidb-export-review")
        self.setWindowTitle("Identification avant encodage")
        self.setMinimumWidth(520)
        self.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        self.browser = None
        self.browser_url = None
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel(
            "Termine l’identification ou le complément dans vidb. Le choix de destination "
            "et la préparation de l’encodage reprendront ici après validation.")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)
        self.status_label = QtWidgets.QLabel("En attente de validation dans vidb…")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.open_button = QtWidgets.QPushButton("Afficher la proposition vidb")
        self.open_button.setVisible(bool(result.get("review_url")))
        self.open_button.clicked.connect(self.open_review)
        layout.addWidget(self.open_button)
        buttons = QtWidgets.QDialogButtonBox(self)
        continuation = "Continuer avec la fiche actuelle" if self.wait_for_change else "Continuer sans association"
        self.continue_button = buttons.addButton(continuation,
                                                  QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        self.continue_button.setAutoDefault(False)
        self.continue_button.clicked.connect(self.accept)
        self.back_button = buttons.addButton("Revenir au montage", QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        self.back_button.setDefault(True)
        self.back_button.clicked.connect(self.reject)
        layout.addWidget(buttons)
        size_vidb_dialog(self)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.poll)
        self.finished.connect(self.finish_review)
        self.timer.start()
        QtCore.QTimer.singleShot(0, self.open_review)

    def open_review(self):
        if self.closed:
            return
        url = self.result_data.get("review_url")
        if url:
            try:
                if self.browser is None:
                    self.browser = build_vidb_browser(self, url)
                    self.layout().insertWidget(2, self.browser, stretch=1)
                    watch_completion(self.browser, url, self.preparation_completed)
                elif hasattr(self.browser, "setUrl"):
                    self.browser.setUrl(QtCore.QUrl(url))
                self.browser_url = url
            except (OSError, ValueError, RuntimeError, ImportError, AttributeError) as error:
                self.status_label.setText(
                    f"Impossible d’ouvrir le navigateur vidb ({type(error).__name__}). "
                    "Le montage reste ouvert ; vérifie Qt WebEngine puis réessaie.")
        else:
            self.status_label.setText(
                "vidb est indisponible. Tu peux revenir au montage ou poursuivre avec une identification à consolider.")

    def preparation_completed(self, record_id):
        self.confirmed_record_id = record_id
        self.next_refresh = 0
        self.status_label.setText("Validation reçue. Vérification de l’association au montage…")
        trace_vidb("form confirmed; waiting for matching project binding")

    def poll(self):
        if self.closed:
            return
        if self.future is None:
            if time.monotonic() >= self.next_refresh:
                self.future = self.executor.submit(self.refresh)
            return
        if not self.future.done():
            return
        try:
            result = self.future.result()
        except Exception:
            self.status_label.setText("vidb est temporairement indisponible ; la vérification va reprendre.")
        else:
            previous = getattr(self, "_trace_last_status", None)
            current = (result.get("status"), result.get("record_id"), self.confirmed_record_id)
            if current != previous:
                trace_vidb(f"export review binding={current[0]}; record={current[1]}; confirmed={current[2]}")
                self._trace_last_status = current
            if result.get("status") != "pending" or self.result_data.get("status") != "identified":
                self.result_data = result
            if result.get("status") == "identified":
                if self.confirmed_record_id is not None and self.confirmed_record_id == result.get("record_id"):
                    self.status_label.setText("Identification validée. Reprise de la préparation…")
                    self.accept()
                    return
                self.continue_button.setText("Continuer avec la fiche identifiée")
                self.status_label.setText(
                    "Fiche reconnue. Confirme la proposition dans vidb, ou continue avec cette fiche.")
            elif result.get("status") == "pending":
                self.status_label.setText("vidb est temporairement indisponible ; la vérification va reprendre.")
            else:
                self.status_label.setText("L’identification reste à valider dans vidb.")
                self.open_button.setVisible(bool(result.get("review_url")))
                if result.get("review_url") and self.browser_url is None:
                    self.open_review()
        self.future = None
        self.next_refresh = time.monotonic() + 3

    def finish_review(self, _result):
        trace_vidb("export review closed; dialog result=" + str(_result))
        self.closed = True
        self.timer.stop()
        self.executor.shutdown(wait=False, cancel_futures=True)


def await_vidb_identification(parent, result, refresh):
    dialog = VidbExportReview(parent, result, refresh)
    outcome = dialog.exec()
    # WebEngine may interrupt the nested modal loop while the dialog is
    # still active. Only finished (which sets closed) ends this workflow.
    if not dialog.closed:
        trace_vidb("modal loop returned before finished; waiting for identification")
        loop = QtCore.QEventLoop()
        dialog.finished.connect(loop.quit)
        try:
            if not dialog.closed:
                loop.exec()
            outcome = dialog.result()
        finally:
            dialog.finished.disconnect(loop.quit)
    if outcome == QtWidgets.QDialog.DialogCode.Accepted:
        return dialog.result_data
    return None
