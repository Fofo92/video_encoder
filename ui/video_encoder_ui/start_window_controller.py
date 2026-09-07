class StartWindowController:
    def __init__(
        self,
        window,
        new_project,
        open_project,
        show_queue,
        quarantine_source,
    ):
        self.window = window
        self.new_project = new_project
        self.open_project = open_project
        self.show_queue = show_queue
        self.quarantine_source = quarantine_source

        self.window.new_project_requested.connect(
            self.new_project
        )
        self.window.open_project_requested.connect(
            self.open_project
        )
        self.window.queue_requested.connect(
            self.show_queue
        )
        self.window.quarantine_requested.connect(
            self.quarantine_source
        )

    def show(self):
        self.window.show()
