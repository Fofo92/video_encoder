from pathlib import Path

from PySide6 import QtWidgets


def select_project_output(parent, suggested, current_project=None):
    """Choose one basename and directory for both the project and its output."""
    selected, _ = QtWidgets.QFileDialog.getSaveFileName(
        parent,
        "Nom et dossier du projet et de la vidéo",
        str(suggested),
        "Vidéo et projet associés (*.mkv)",
        options=QtWidgets.QFileDialog.Option.DontConfirmOverwrite,
    )
    if not selected:
        return None

    output = Path(selected).expanduser()
    if not output.suffix:
        output = output.with_suffix(".mkv")
    error = destination_error(output, current_project)
    if error:
        QtWidgets.QMessageBox.warning(parent, "Destination invalide", error)
        return None
    return output


def destination_error(output, current_project=None):
    if output.suffix.lower() != ".mkv":
        return "Choisis un nom sans extension ou un fichier .mkv."
    if not output.parent.is_dir():
        return "Le dossier de destination n’existe pas."
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
