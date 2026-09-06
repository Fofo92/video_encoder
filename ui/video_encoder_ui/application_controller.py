from .start_window_controller import (
    StartWindowController,
)

class ApplicationController:
    def __init__(
        self,
        start_window,
        select_source,
        select_project,
        open_editor,
        queue_controller,
        start_controller_class=StartWindowController,
    ):
        self.start_window = start_window
        self.select_source = select_source
        self.select_project = select_project
        self.open_editor = open_editor
        self.queue_controller = queue_controller

        self.start_controller = (
            start_controller_class(
                window=start_window,
                new_project=self.new_project,
                open_project=self.open_project,
                show_queue=self.show_queue,
            )
        )

    def show(self):
        self.start_controller.show()

    def new_project(self):
        source_path = self.select_source()

        if source_path is None:
            return

        self.open_editor(source_path)

    def open_project(self):
        project_path = self.select_project()

        if project_path is None:
            return

        self.open_editor(project_path)

    def show_queue(self):
        self.queue_controller.show()

    def queue_status_changed(self, status):
        self.start_window.set_queue_running(
            status == "running"
        )
