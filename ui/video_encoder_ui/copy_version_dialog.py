"""Explicit VOST review, shared by the desktop menu and a vidb copy launch."""
from pathlib import Path
import subprocess

from PySide6 import QtWidgets

from .copy_version import enqueue, pipeline, suggested_output
from .trim_export_queue_client import TrimExportQueueError
from .vidb_project_link import VidbProjectLink


def choose_original(parent, source, details):
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Changer de version — VOST")
    layout = QtWidgets.QVBoxLayout(dialog)
    label = QtWidgets.QLabel(
        f"{source.name}\nVOST : une piste originale et les sous-titres français déjà dans l’image.\n"
        "La vidéo et l’audio sont copiés sans réencodage. Les autres pistes sont retirées de la nouvelle copie.")
    label.setWordWrap(True)
    layout.addWidget(label)
    tracks = QtWidgets.QComboBox(dialog)
    for row in details["streams"]:
        if row["codec_type"] != "audio" or row.get("disposition", {}).get("visual_impaired"):
            continue
        tags = row.get("tags", {})
        tracks.addItem(f"Piste {row['index']} · {tags.get('language', 'non renseignée')} · "
                       f"{tags.get('title', row.get('codec_name', 'audio'))}", row["index"])
    tracks.setCurrentIndex(-1)
    layout.addWidget(QtWidgets.QLabel("Piste originale à conserver :"))
    layout.addWidget(tracks)
    heard = QtWidgets.QCheckBox("J’ai vérifié à l’écoute que cette piste est la version originale.")
    burned = QtWidgets.QCheckBox("J’ai vérifié que les sous-titres français sont incrustés dans l’image.")
    for checkbox in (heard, burned):
        layout.addWidget(checkbox)
    layout.addWidget(QtWidgets.QLabel("L’ancienne copie est conservée. Le travail sera ajouté à la file."))
    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
    ok = buttons.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
    ok.setText("Continuer")
    def update():
        ok.setEnabled(tracks.currentIndex() >= 0 and heard.isChecked() and burned.isChecked())
    tracks.currentIndexChanged.connect(update)
    heard.toggled.connect(update)
    burned.toggled.connect(update)
    update()
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    accepted = dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted
    result = tracks.currentData() if accepted else None
    dialog.deleteLater()
    return result


def identify(parent, document, output, link, context):
    project = output.with_suffix(".json")
    result = link.identify(document, project)
    if context and result.get("status") != "identified":
        raise ValueError(result.get("reason") or "L’association à la copie vidb n’a pas pu être confirmée.")
    if result.get("status") not in ("identified", "disabled"):
        from .vidb_export_review import await_vidb_identification
        result = await_vidb_identification(parent, result, lambda: link.identify(document, project, refresh=True))
        if result is None:
            return False
    if result.get("status") == "identified":
        if context and result.get("record_id") != context["record_id"]:
            raise ValueError("La fiche associée a changé : reprends la préparation depuis vidb.")
        document["vidb"] = result
        document.pop("vidb_launch", None)
    return True


def confirm_queue(parent, source, output):
    box = QtWidgets.QMessageBox(parent)
    box.setWindowTitle("Changer de version — mise en file")
    box.setText(f"VOST · une piste originale · sous-titres français incrustés\n\n"
                f"Source : {source}\nNouvelle copie : {output}\n\n"
                "Copie sans réencodage. L’ancienne copie est conservée.")
    add = box.addButton("Ajouter à la file d’attente", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton("Annuler", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    return box.clickedButton() is add


def prepare_copy_version(parent, queue, *, source=None, context=None, ticket=None, link=None):
    try:
        if parent.isMinimized():
            parent.showNormal()
        parent.show()
        parent.raise_()
        parent.activateWindow()
        if source is None:
            selected, _ = QtWidgets.QFileDialog.getOpenFileName(
                parent, "Changer de version — copie encodée", "/videos", "Copie MKV (*.mkv)")
            if not selected:
                return False
            source = selected
        source = Path(source).absolute()
        before = pipeline().identity(source)
        details = pipeline().probe(source)
        audio_index = choose_original(parent, source, details)
        if audio_index is None:
            return False
        if before != pipeline().identity(source):
            raise ValueError("La copie source a changé pendant la préparation.")
        document = pipeline().prepare(source, audio_index, original_confirmed=True,
                                      burned_french_confirmed=True, details=details)
        if context:
            document["vidb_launch"] = ticket
        selected, _ = QtWidgets.QFileDialog.getSaveFileName(
            parent, "Nouvelle copie VOST — conserver l’ancienne", str(suggested_output(source)), "Copie MKV (*.mkv)")
        if not selected:
            return False
        output = Path(selected).absolute()
        if output.exists() or output.is_symlink() or output.with_suffix(".json").exists():
            raise ValueError("Cette destination existe déjà : choisis un nouveau nom.")
        if not confirm_queue(parent, source, output):
            return False
        if not identify(parent, document, output, link or VidbProjectLink(), context):
            return False
        enqueue(document, output, queue)
        QtWidgets.QMessageBox.information(parent, "Changement de version en attente",
                                         "VOST ajoutée à la file. L’ancienne copie est conservée.\n"
                                         "La nouvelle copie sera reconnue par vidb après réussite et actualisation de l’inventaire.")
        return True
    except (OSError, ValueError, KeyError, TypeError, StopIteration, subprocess.SubprocessError,
            TrimExportQueueError) as error:
        QtWidgets.QMessageBox.warning(parent, "Changement de version non préparé", str(error))
        return False
