from PySide6 import QtCore

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
        editor_window = self.editor_factory(
            selected_path
        )

        if editor_window is None:
            return

        self.editor_window = editor_window
        editor_window.setAttribute(
            QtCore.Qt.WidgetAttribute.WA_DeleteOnClose,
            True,
        )
        editor_window.destroyed.connect(
            self.editor_closed
        )
        editor_window.show()
        self.start_window.hide()

    def editor_closed(self, *_arguments):
        self.editor_window = None
        self.start_window.show()
