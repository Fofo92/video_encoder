from PySide6 import QtWidgets

from .trim_export_queue_client import TrimExportQueueError


def remove_project(parent, client):
    path, _filter = QtWidgets.QFileDialog.getOpenFileName(
        parent, "Supprimer un projet", "", "Projet video_encoder (*.json)")
    if not path:
        return
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Supprimer un projet")
    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel(path)
    label.setWordWrap(True)
    layout.addWidget(label)
    dependencies = QtWidgets.QCheckBox("Inclure les vidéos encodées et leurs reçus")
    layout.addWidget(dependencies)
    note = QtWidgets.QLabel(
        "Les captures sources sont conservées. Les fichiers seront déplacés dans un dossier "
        "de récupération .video_encoder_trash voisin du projet. Les tâches ne sont pas supprimées.")
    note.setWordWrap(True)
    layout.addWidget(note)
    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Examiner les fichiers…")
    buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setDefault(True)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        dialog.deleteLater()
        return
    include = dependencies.isChecked()
    dialog.deleteLater()
    try:
        plan = client.remove_project_files(path, dependencies=include)
        answer = QtWidgets.QMessageBox.question(
            parent, "Confirmer la suppression du projet",
            "Déplacer uniquement ces fichiers vers le dossier de récupération ?\n\n"
            + "\n".join(plan['files']),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No)
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return
        directory = client.remove_project_files(path, dependencies=include, token=plan['token'])
        QtWidgets.QMessageBox.information(parent, "Projet supprimé", f"Récupération possible dans :\n{directory}")
    except (TrimExportQueueError, ValueError, KeyError, TypeError) as error:
        QtWidgets.QMessageBox.warning(parent, "Suppression impossible", str(error))
