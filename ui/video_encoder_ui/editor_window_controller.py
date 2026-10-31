import logging


class EditorWindowController:
    def __init__(
        self,
        start_window,
        editor_factory,
    ):
        self.start_window = start_window
        self.editor_factory = editor_factory
        self.editor_window = None

    def open(self, selected_path):
        previous = self.editor_window
        if previous is not None and not previous.close():
            return
        try:
            editor_window = self.editor_factory(selected_path)
        except Exception as error:
            # Qt slots otherwise report Python exceptions only to stderr.
            logging.exception("Impossible d’ouvrir le montage : %s", selected_path)
            from PySide6 import QtWidgets

            QtWidgets.QMessageBox.critical(
                self.start_window, "Montage non ouvert",
                f"Fichier : {selected_path}\n\n{type(error).__name__} : {error}")
            return

        if editor_window is None:
            return

        self.editor_window = editor_window

        editor_window.destroyed.connect(
            lambda *_arguments: self.editor_closed(editor_window)
        )
        self.start_window.show()
        editor_window.show()
        editor_window.raise_()
        editor_window.activateWindow()
        for name in ("relocate_project_action", "quarantine_action", "delete_project_action", "project_trash_action"):
            action = getattr(self.start_window, name, None)
            if action is not None:
                action.setEnabled(False)

    def editor_closed(self, closed_window=None, *_arguments):
        if closed_window is not None and closed_window is not self.editor_window:
            return
        self.editor_window = None
        self.start_window.show()
        for name in ("relocate_project_action", "quarantine_action", "delete_project_action", "project_trash_action"):
            action = getattr(self.start_window, name, None)
            if action is not None:
                action.setEnabled(True)

