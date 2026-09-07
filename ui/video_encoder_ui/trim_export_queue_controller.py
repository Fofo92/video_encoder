from PySide6 import QtCore, QtWidgets

from video_encoder_ui.trim_export_queue_client import (
    TrimExportQueueError,
)


class TrimExportQueueController:
    def __init__(
        self,
        client,
        runner,
        dialog_class,
        parent=None,
    ):
        self.client = client
        self.runner = runner
        self.dialog_class = dialog_class
        self.runner.succeeded.connect(
            self.succeeded
        )
        self.runner.failed.connect(
            self.failed
        )
        self.parent = parent
        self.dialog = None

    def show(self):
        try:
            jobs = self.client.list_jobs()
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "File indisponible",
                str(error),
            )
            return

        dialog = self.dialog_class(
            jobs,
            self.parent,
        )
        self.dialog = dialog

        dialog.set_running(
            self.runner.is_running
        )
        dialog.refresh_requested.connect(
            lambda: self.refresh(dialog)
        )
        dialog.start_requested.connect(
            lambda: self.start(dialog)
        )

        dialog.retry_requested.connect(
            lambda job: self.retry(dialog, job)
        )

        dialog.exec()

        if self.dialog is dialog:
            self.dialog = None

    def refresh(self, dialog):
        try:
            jobs = self.client.list_jobs()
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Actualisation impossible",
                str(error),
            )
            return

        dialog.set_jobs(jobs)
        dialog.mark_refreshed(
            QtCore.QTime.currentTime().toString(
                "HH:mm:ss"
            )
        )

    def retry(self, dialog, job):
        answer = QtWidgets.QMessageBox.question(
            self.parent,
            "Relancer le montage",
            (
                "Créer un nouveau travail à partir "
                "du montage en échec ?\n\n"
                f"Projet : {job['input_path']}\n"
                f"Sortie : {job['output_path']}\n\n"
                "Le travail en échec restera dans "
                "l’historique."
            ),
            (
                QtWidgets.QMessageBox.StandardButton.Yes
                | QtWidgets.QMessageBox.StandardButton.No
            ),
            QtWidgets.QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QtWidgets.QMessageBox.StandardButton.Yes
        ):
            return

        try:
            self.client.enqueue(
                job["input_path"],
                job["output_path"],
            )
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Relance impossible",
                str(error),
            )
            return

        self.refresh(dialog)

    def start(self, dialog):
        try:
            self.runner.start()
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Lancement impossible",
                str(error),
            )
            return

        dialog.set_running(True)

    def succeeded(self):
        dialog = self.dialog

        if dialog is not None:
            dialog.set_running(False)
            self.refresh(dialog)

        QtWidgets.QMessageBox.information(
            self.parent,
            "File terminée",
            (
                "Tous les montages en attente "
                "ont été traités."
            ),
        )

    def failed(self, message):
        dialog = self.dialog

        if dialog is not None:
            dialog.set_running(False)
            self.refresh(dialog)

        QtWidgets.QMessageBox.warning(
            self.parent,
            "Échec de la file",
            message,
        )
