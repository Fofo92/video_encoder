from pathlib import Path

from PySide6 import QtWidgets

from .montage_condition import checked_condition, declaration, needs_review, source_paths


class MontageConditionDialog(QtWidgets.QDialog):
    def __init__(self, parent, session):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle("État de la copie à encoder")
        self.resize(620, 300)
        current = getattr(session, "copy_condition", None)
        current = checked_condition(current) if current is not None else {}
        layout = QtWidgets.QVBoxLayout(self)
        explanation = QtWidgets.QLabel(
            "Décris le montage conservé : un défaut coupé ou remplacé ne compte pas.\n"
            "Cet état concernera cette copie dans vidb, après l’encodage.")
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        form = QtWidgets.QFormLayout()
        self.integrality = QtWidgets.QComboBox()
        for label, code in (("Complète", "complete"), ("Incomplète", "incomplete"),
                            ("Début seulement", "beginning"), ("Fin seulement", "end")):
            self.integrality.addItem(label, code)
        portion = current.get("retained_portion", "unknown")
        selected = portion if portion != "unknown" else current.get("integrality", "complete")
        self.integrality.setCurrentIndex(self.integrality.findData(selected))
        form.addRow("Complétude", self.integrality)
        self.damage = QtWidgets.QComboBox()
        for label, code in (("Aucune", "none"), ("Légère", "light"), ("Importante", "severe")):
            self.damage.addItem(label, code)
        self.damage.setCurrentIndex(self.damage.findData(current.get("damage", "none")))
        form.addRow("Détérioration", self.damage)
        self.source = QtWidgets.QComboBox()
        self.source.addItem("Montage entier / plusieurs sources", None)
        for path in source_paths(session):
            self.source.addItem(Path(path).name, path)
            self.source.setItemData(self.source.count() - 1, path, 3)
        affected = current.get("affected_source_paths", [])
        if len(affected) == 1:
            self.source.setCurrentIndex(max(0, self.source.findData(affected[0])))
        form.addRow("Source concernée", self.source)
        self.note = QtWidgets.QPlainTextEdit(current.get("note", ""))
        self.note.setPlaceholderText("Passage manquant, image ou son abîmé… (facultatif)")
        self.note.setMaximumHeight(90)
        form.addRow("Note", self.note)
        layout.addLayout(form)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def condition(self):
        selected = self.integrality.currentData()
        return declaration(self.session, integrality="complete" if selected == "complete" else "incomplete",
                           damage=self.damage.currentData(),
                           retained_portion=selected if selected in ("beginning", "end") else "unknown",
                           note=self.note.toPlainText().strip(),
                           affected_source_paths=[self.source.currentData()] if self.source.currentData() else [])

    def accept(self):
        try:
            self.condition()
        except ValueError as error:
            QtWidgets.QMessageBox.warning(self, "État du montage", str(error))
            return
        super().accept()


def review_montage_condition(parent, session, *, force=False):
    if not force and not needs_review(session):
        return True
    dialog = MontageConditionDialog(parent, session)
    if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return False
    session.copy_condition = dialog.condition()
    parent.set_project_modified(True)
    return True
