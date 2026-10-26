from pathlib import Path

from PySide6 import QtWidgets


def select_project_output(parent, suggested, current_project=None):
    """Choose one basename and directory for both the project and its output."""
    selected, _ = choose_project_output(parent, suggested)
    if not selected:
        return None

    output = Path(selected).expanduser()
    if not output.suffix:
        output = output.with_suffix(".mkv")
    error = destination_error(output, current_project)
    if error:
        QtWidgets.QMessageBox.warning(parent, "Destination invalide", error)
        return None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        QtWidgets.QMessageBox.warning(parent, "Destination invalide", f"Impossible de créer le dossier : {error}")
        return None
    return output


def destination_error(output, current_project=None):
    if output.suffix.lower() != ".mkv":
        return "Choisis un nom sans extension ou un fichier .mkv."
    if any(parent.exists() and not parent.is_dir() for parent in output.parents):
        return "Un élément du chemin est un fichier, pas un dossier."
    if output.exists() or output.is_symlink():
        return "Une vidéo existe déjà à cette destination. Choisis un autre nom."

    project = output.with_suffix(".json")
    if project.name == "proposal.json":
        return "Choisis un autre nom pour préserver la proposition automatique."
    if project.is_symlink():
        return "Le projet de destination est un lien symbolique."
    same_project = current_project is not None and project.resolve() == Path(current_project).resolve()
    if project.exists() and (not same_project or not project.is_file()):
        return "Un autre projet JSON existe déjà à cette destination. Choisis un autre nom."
    return None


def choose_project_output(parent, suggested):
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Nom et dossier du projet et de la vidéo")
    dialog.resize(800, 160)
    layout = QtWidgets.QVBoxLayout(dialog)
    layout.addWidget(QtWidgets.QLabel("Chemin complet ; les sous-dossiers manquants seront créés."))
    row = QtWidgets.QHBoxLayout()
    path = QtWidgets.QLineEdit(str(suggested))
    path.setObjectName("project-output-path")
    row.addWidget(path)
    browse = QtWidgets.QPushButton("Parcourir…")
    row.addWidget(browse)
    layout.addLayout(row)

    def browse_directory():
        current = Path(path.text()).expanduser()
        initial = next((p for p in current.parents if p.is_dir()), Path.home())
        selected = QtWidgets.QFileDialog.getExistingDirectory(dialog, "Dossier de destination", str(initial))
        if selected:
            path.setText(str(Path(selected) / current.name))

    browse.clicked.connect(browse_directory)
    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Save | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    accepted = dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
    return (path.text().strip(), "") if accepted else ("", "")
