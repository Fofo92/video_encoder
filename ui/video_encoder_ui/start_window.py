from PySide6 import QtCore, QtWidgets


class StartWindow(QtWidgets.QWidget):
    new_project_requested = QtCore.Signal()
    open_project_requested = QtCore.Signal()
    queue_requested = QtCore.Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("video_encoder")
        self.setMinimumWidth(420)

        title_label = QtWidgets.QLabel(
            "Que souhaites-tu faire ?",
            self,
        )
        title_label.setAlignment(
            QtCore.Qt.AlignmentFlag.AlignCenter
        )

        self.new_project_button = QtWidgets.QPushButton(
            "Nouveau montage…",
            self,
        )
        self.open_project_button = QtWidgets.QPushButton(
            "Ouvrir un projet de découpage…",
            self,
        )
        self.queue_button = QtWidgets.QPushButton(
            "File des montages…",
            self,
        )

        self.new_project_button.clicked.connect(
            self.new_project_requested
        )
        self.open_project_button.clicked.connect(
            self.open_project_requested
        )
        self.queue_button.clicked.connect(
            self.queue_requested
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(12)

        layout.addWidget(title_label)
        layout.addSpacing(12)
        layout.addWidget(self.new_project_button)
        layout.addWidget(self.open_project_button)
        layout.addWidget(self.queue_button)
        layout.addStretch()
