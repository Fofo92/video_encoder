class StartWindowController:
    def __init__(
        self,
        window,
        new_project,
        open_project,
        show_queue,
    ):
        self.window = window
        self.new_project = new_project
        self.open_project = open_project
        self.show_queue = show_queue

        self.window.new_project_requested.connect(
            self.new_project
        )
        self.window.open_project_requested.connect(
            self.open_project
        )
        self.window.queue_requested.connect(
            self.show_queue
        )

    def show(self):
        self.window.show()
