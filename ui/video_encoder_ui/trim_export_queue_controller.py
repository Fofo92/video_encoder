from PySide6 import QtCore, QtWidgets
from .project_destination import select_project_output

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
        self.runner.interrupted.connect(
            self.interrupted
        )
        self.runner.stopped.connect(
            self.stopped
        )
        self.runner.failed.connect(
            self.failed
        )
        self.runner.progress_changed.connect(
            self.progress_changed
        )
        self.runner.percentage_changed.connect(
            self.percentage_changed
        )
        self.parent = parent
        self.dialog = None
        self.selected_job_id = None
        self.continue_after_current = False

    def show(self):
        if self.dialog is not None:
            self.refresh(self.dialog)
            self.dialog.show()
            self.dialog.raise_()
            self.dialog.activateWindow()
            return
        try:
            jobs = self.client.list_jobs()
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(self.parent, "File indisponible", str(error))
            return
        dialog = self.dialog_class(jobs, self.parent)
        self.attach(dialog)
        dialog.exec()
        if self.dialog is dialog:
            self.dialog = None

    def attach(self, dialog):
        self.dialog = dialog
        dialog.set_running(self.runner.is_running)
        dialog.set_single_job_running(self.selected_job_id is not None)
        dialog.set_continue_after_current_requested(self.continue_after_current)
        dialog.refresh_requested.connect(lambda: self.refresh(dialog))
        dialog.start_requested.connect(lambda: self.start(dialog))
        dialog.start_selected_requested.connect(lambda job: self.start_selected(dialog, job))
        dialog.stop_requested.connect(lambda: self.stop(dialog))
        dialog.finish_current_requested.connect(lambda: self.finish_current(dialog))
        dialog.retry_requested.connect(lambda job: self.retry(dialog, job))
        dialog.remove_requested.connect(lambda job: self.remove(dialog, job))
        dialog.defer_requested.connect(lambda job: self.defer(dialog, job))
        dialog.output_requested.connect(lambda job: self.change_output(dialog, job))
        dialog.delete_project_requested.connect(lambda job: self.delete_project(dialog, job))

    def relocate_project(self):
        from pathlib import Path

        job = self.dialog.selected_job() if self.dialog is not None else None
        project = job.get("input_path") if job is not None else None
        if not project:
            project, _filter = QtWidgets.QFileDialog.getOpenFileName(
                self.parent, "Projet à déplacer ou renommer", "/videos", "Projet JSON (*.json)")
        if not project:
            return
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self.parent, "Dossier cible — conserver le dossier actuel pour renommer", str(Path(project).parent))
        if not directory:
            return
        name, accepted = QtWidgets.QInputDialog.getText(
            self.parent, "Nom du projet et de sa vidéo",
            "Nom commun, sans extension :", text=Path(project).stem)
        if not accepted:
            return
        name = name if name != Path(project).stem else None
        try:
            plan = self.client.move_project(project, directory, name=name, preview=True)
            changes = "\n\n".join(f"{item['source']}\n→ {item['destination']}" for item in plan["files"])
            outputs = "\n".join(plan["outputs"])
            answer = QtWidgets.QMessageBox.question(
                self.parent, "Confirmer le déplacement ou renommage",
                f"Fichiers concernés :\n\n{changes}\n\nSorties prévues :\n{outputs}\n\n"
                "Les chemins de la file et des reçus seront actualisés.\n"
                "Les captures sources et les bornes de découpage seront conservées.\n"
                "Les liens de vidéothèque vidb seront à rapprocher après cette opération.",
                QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                QtWidgets.QMessageBox.StandardButton.No)
            if answer != QtWidgets.QMessageBox.StandardButton.Yes:
                return
            destination = self.client.move_project(project, directory, name=name)
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(self.parent, "Déplacement ou renommage impossible", str(error))
            return
        if self.dialog is not None:
            self.refresh(self.dialog)
        QtWidgets.QMessageBox.information(self.parent, "Projet déplacé ou renommé", destination)

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
                "du montage non terminé ?\n\n"
                f"Projet : {job['input_path']}\n"
                f"Sortie : {job['output_path']}\n\n"
                "Le travail précédent restera dans "
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

    def remove(self, dialog, job):
        answer = QtWidgets.QMessageBox.question(
            self.parent,
            "Supprimer la tâche",
            (
                "Supprimer cette tâche de la liste ?\n\n"
                f"Projet : {job['input_path']}\n"
                f"Sortie : {job['output_path']}\n\n"
                "Le projet, les sources et le fichier de sortie "
                "ne seront pas supprimés."
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
            self.client.remove(job["id"])
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Suppression impossible",
                str(error),
            )
            return

        self.refresh(dialog)

    def defer(self, dialog, job):
        try:
            if job["status"] == "deferred":
                self.client.resume(job["id"])
            elif job["status"] == "queued":
                self.client.defer(job["id"])
            else:
                return
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(self.parent, "Report impossible", str(error))
            return
        self.refresh(dialog)

    def change_output(self, dialog, job):
        if self.runner.is_running or job.get("status") not in ("queued", "deferred"):
            return
        path = select_project_output(self.parent, job["output_path"], job.get("input_path"))
        if path is None:
            return
        try:
            self.client.set_output(job["id"], path)
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(self.parent, "Destination impossible", str(error))
            return
        self.refresh(dialog)

    def delete_project(self, dialog, job):
        if job.get("status") == "running":
            return
        answer = QtWidgets.QMessageBox.question(
            self.parent, "Supprimer la tâche et son projet",
            f"Supprimer définitivement cette tâche et le fichier JSON suivant ?\n\n{job['input_path']}\n\n"
            "Les sources vidéo, le fichier encodé et son reçu seront conservés. "
            "Un projet utilisé par une autre tâche ne peut pas être supprimé.",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        try:
            self.client.delete_project(job["id"])
        except TrimExportQueueError as error:
            QtWidgets.QMessageBox.warning(self.parent, "Suppression impossible", str(error))
            return
        self.refresh(dialog)

    def start(self, dialog):
        if self.runner.is_running:
            if self.selected_job_id is not None or self.runner.finish_current_requested:
                self.continue_after_current = True
                dialog.set_continue_after_current_requested(True)
            return
        try:
            self.runner.start()
            self.selected_job_id = None
            self.continue_after_current = False
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Lancement impossible",
                str(error),
            )
            return

        dialog.set_running(True)
        dialog.set_single_job_running(False)
        dialog.set_continue_after_current_requested(False)

    def start_selected(self, dialog, job):
        try:
            if self.runner.is_running:
                raise RuntimeError("Un encodage est déjà en cours.")
            jobs = self.client.list_jobs()
            selected = next((item for item in jobs if item.get("id") == job.get("id")), None)
            if selected is None or selected.get("status") != "queued":
                raise RuntimeError("La tâche sélectionnée n’est plus en attente. Actualise la file.")
            if any(item.get("status") == "running" for item in jobs):
                raise RuntimeError("Un encodage est déjà en cours.")
            self.runner.start(job_id=selected["id"])
            self.selected_job_id = selected["id"]
            self.continue_after_current = False
        except (TrimExportQueueError, RuntimeError) as error:
            QtWidgets.QMessageBox.warning(self.parent, "Lancement impossible", str(error))
            return
        dialog.set_running(True)
        dialog.set_single_job_running(True)
        dialog.set_continue_after_current_requested(False)

    def stop(self, dialog):
        answer = QtWidgets.QMessageBox.question(
            self.parent,
            "Interrompre la file",
            (
                "Interrompre le montage en cours ?\n\n"
                "Le travail courant sera marqué comme "
                "interrompu. Les autres montages "
                "resteront en attente."
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
            self.runner.stop()
            self.continue_after_current = False
            dialog.set_continue_after_current_requested(False)
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Interruption impossible",
                str(error),
            )

    def finish_current(self, dialog):
        answer = QtWidgets.QMessageBox.question(
            self.parent,
            "Arrêter après le montage en cours",
            (
                "Terminer le montage en cours puis "
                "arrêter la file ?\n\n"
                "Les autres montages resteront "
                "en attente."
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
            self.runner.finish_current()
            self.continue_after_current = False
            dialog.set_continue_after_current_requested(False)
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(
                self.parent,
                "Arrêt différé impossible",
                str(error),
            )
            return

        dialog.set_finish_current_requested(True)

    def resume_requested_queue(self, dialog):
        if not self.continue_after_current:
            return False
        self.continue_after_current = False
        self.selected_job_id = None
        if dialog is not None:
            dialog.set_running(False)
        try:
            self.runner.start()
        except RuntimeError as error:
            QtWidgets.QMessageBox.warning(self.parent, "Suite non lancée", str(error))
            return True
        if dialog is not None:
            dialog.set_running(True)
            dialog.set_single_job_running(False)
            dialog.set_continue_after_current_requested(False)
            self.refresh(dialog)
        return True

    def succeeded(self):
        selected = self.selected_job_id is not None
        self.selected_job_id = None
        dialog = self.dialog
        if self.resume_requested_queue(dialog):
            return

        if dialog is not None:
            dialog.set_running(False)
            self.refresh(dialog)

        QtWidgets.QMessageBox.information(
            self.parent,
            "Montage terminé" if selected else "File terminée",
            ("La tâche sélectionnée est terminée. Les autres montages restent en attente."
             if selected else "Tous les montages en attente ont été traités."),
        )

    def interrupted(self):
        self.selected_job_id = None
        self.continue_after_current = False
        dialog = self.dialog

        if dialog is not None:
            dialog.set_running(False)
            self.refresh(dialog)

        QtWidgets.QMessageBox.information(
            self.parent,
            "File interrompue",
            (
                "Le montage en cours a été interrompu. "
                "Les autres montages restent en attente."
            ),
        )

    def stopped(self):
        self.selected_job_id = None
        dialog = self.dialog
        if self.resume_requested_queue(dialog):
            return

        if dialog is not None:
            dialog.set_running(False)
            self.refresh(dialog)

        QtWidgets.QMessageBox.information(
            self.parent,
            "File arrêtée",
            (
                "Le montage en cours est terminé. "
                "Les autres montages restent en attente."
            ),
        )

    def progress_changed(self, event):
        dialog = self.dialog

        if dialog is not None:
            dialog.set_progress(event)

    def percentage_changed(self, percentage):
        dialog = self.dialog

        if dialog is not None:
            dialog.set_percentage(percentage)

    def failed(self, message):
        self.selected_job_id = None
        dialog = self.dialog
        if self.continue_after_current:
            self.resume_requested_queue(dialog)
            QtWidgets.QMessageBox.warning(self.parent, "Échec du montage précédent", message)
            return

        if dialog is not None:
            dialog.set_running(False)
            self.refresh(dialog)

        QtWidgets.QMessageBox.warning(
            self.parent,
            "Échec de la file",
            message,
        )
