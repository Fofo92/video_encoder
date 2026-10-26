from pathlib import Path

from PySide6 import QtWidgets


def select_quarantine_sources():
    selected, _filter = QtWidgets.QFileDialog.getOpenFileNames(
        None, "Mettre des sources en quarantaine", "/commun/to_be_cut",
        "Enregistrements TV (*.m2t *.mts *.ts);;Tous les fichiers (*)")
    return list(dict.fromkeys(Path(path).expanduser().resolve() for path in selected)) or None


def confirm_quarantine_sources(parent, selected):
    paths = selected if isinstance(selected, (list, tuple)) else [selected]
    box = QtWidgets.QMessageBox(parent)
    box.setWindowTitle("Confirmer la mise en quarantaine")
    box.setText(f"Mettre {len(paths)} source(s) en quarantaine ?")
    box.setInformativeText(
        "Chaque source peut contenir plusieurs films ou épisodes.\n"
        "Confirme que tous les programmes utiles de chaque source ont été encodés.\n"
        "Les fichiers seront déplacés en quarantaine, sans suppression définitive.")
    box.setDetailedText("\n".join(str(path) for path in paths))
    box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No)
    box.setDefaultButton(QtWidgets.QMessageBox.StandardButton.No)
    return box.exec() == QtWidgets.QMessageBox.StandardButton.Yes


def report_quarantine_batch(parent, moved, failed):
    box = QtWidgets.QMessageBox(parent)
    box.setWindowTitle("Bilan de la quarantaine")
    box.setText(f"{len(moved)} source(s) déplacée(s) ; {len(failed)} conservée(s).")
    box.setDetailedText("\n".join([f"Déplacée : {path}" for path in moved]
                                 + [f"Conservée : {path} — {reason}" for path, reason in failed]))
    box.setIcon(QtWidgets.QMessageBox.Icon.Warning if failed else QtWidgets.QMessageBox.Icon.Information)
    box.exec()
