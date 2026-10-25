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
        editor_window = self.editor_factory(selected_path)

        if editor_window is None:
            return

        self.editor_window = editor_window

        editor_window.destroyed.connect(
            lambda *_arguments: self.editor_closed(editor_window)
        )
        editor_window.show()
        self.start_window.show()
        for name in ("relocate_project_action", "quarantine_action"):
            action = getattr(self.start_window, name, None)
            if action is not None:
                action.setEnabled(False)

    def editor_closed(self, closed_window=None, *_arguments):
        if closed_window is not None and closed_window is not self.editor_window:
            return
        self.editor_window = None
        self.start_window.show()
        for name in ("relocate_project_action", "quarantine_action"):
            action = getattr(self.start_window, name, None)
            if action is not None:
                action.setEnabled(True)
