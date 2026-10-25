from PySide6 import QtCore, QtGui, QtWidgets


def offer_vidb_review(parent, writer, before_encoding=False):
    result = getattr(writer, "vidb_result", None)
    if not isinstance(result, dict) or result.get("status") in {"identified", "disabled"}:
        return True
    dialog = QtWidgets.QMessageBox(parent)
    dialog.setWindowTitle("Identification de l’œuvre dans vidb")
    dialog.setText("Le projet est enregistré ; son association à une fiche vidb reste à compléter.")
    explanations = {
        "needs_review": "Vérifie les propositions dans vidb, puis relance l’identification depuis le menu Montage.",
        "unmatched": "Aucune fiche compatible n’a été trouvée. Complète le catalogue dans vidb, puis réessaie.",
        "pending": "vidb est indisponible. La demande est conservée ; tu peux encoder et reprendre l’identification plus tard.",
    }
    dialog.setInformativeText(explanations.get(result.get("status"), "L’identification reste à compléter."))
    open_button = None
    if result.get("review_url"):
        open_button = dialog.addButton("Vérifier dans vidb", QtWidgets.QMessageBox.ButtonRole.ActionRole)
        dialog.setDefaultButton(open_button)
    continue_button = dialog.addButton("Encoder sans association" if before_encoding else "Continuer le montage",
                                       QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    dialog.addButton("Revenir au montage", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    dialog.exec()
    if open_button is not None and dialog.clickedButton() is open_button:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(result["review_url"]))
        return False
    return dialog.clickedButton() is continue_button
