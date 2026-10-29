from PySide6 import QtCore, QtGui, QtWidgets

from .trim_export_queue_dialog import TrimExportQueueDialog
from .window_placement import place_initial_window


class StartWindow(TrimExportQueueDialog):
    """The queue is the application's home, including source/project actions."""
    new_project_requested = QtCore.Signal()
    open_project_requested = QtCore.Signal()
    queue_requested = QtCore.Signal()
    quarantine_requested = QtCore.Signal()
    relocate_requested = QtCore.Signal()

    def __init__(self):
        super().__init__(jobs=[])
        self.setWindowTitle("video_encoder — Montages")
        self.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.menu_bar = QtWidgets.QMenuBar(self)
        self.layout().setMenuBar(self.menu_bar)
        sources = QtWidgets.QMenu("&Sources", self.menu_bar)
        projects = QtWidgets.QMenu("&Projets", self.menu_bar)
        montages = QtWidgets.QMenu("&Montage", self.menu_bar)
        self.home_menus = (sources, projects, montages)
        for menu in self.home_menus:
            self.menu_bar.addMenu(menu)
        self.new_project_action = self.add_home_action(
            sources, "Ouvrir une source…", "document-new", self.new_project_requested)
        self.quarantine_action = self.add_home_action(
            sources, "Mettre des sources en quarantaine…", "folder-move", self.quarantine_requested)
        self.open_project_action = self.add_home_action(
            projects, "Ouvrir un projet…", "document-open", self.open_project_requested, "Ctrl+O")
        self.relocate_project_action = self.add_home_action(
            projects, "Déplacer ou renommer un projet et sa vidéo…", "folder-move", self.relocate_requested)
        self.new_montage_action = self.add_home_action(
            montages, "Nouveau montage…", "document-new", self.new_project_requested, "Ctrl+N")
        for button in (self.start_button, self.stop_button, self.finish_current_button):
            action = montages.addAction(button.text())
            action.triggered.connect(button.click)
            button.installEventFilter(self)
            button.setProperty("home_menu_action", action)
            action.setEnabled(button.isEnabled())
        names = {
            self.start_button: ("media-playback-start", QtWidgets.QStyle.StandardPixmap.SP_MediaPlay),
            self.stop_button: ("media-playback-stop", QtWidgets.QStyle.StandardPixmap.SP_MediaStop),
            self.finish_current_button: ("media-playback-pause", QtWidgets.QStyle.StandardPixmap.SP_MediaPause),
            self.retry_button: ("view-refresh", QtWidgets.QStyle.StandardPixmap.SP_BrowserReload),
            self.refresh_button: ("view-refresh", QtWidgets.QStyle.StandardPixmap.SP_BrowserReload),
        }
        for button, (name, fallback) in names.items():
            self.set_action_icon(button, name, fallback)
        for box in (self.queue_buttons, self.job_buttons):
            group = box.parentWidget()
            toolbar = QtWidgets.QToolBar(group)
            toolbar.setIconSize(QtCore.QSize(22, 22))
            toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            for button in box.buttons():
                action = toolbar.addAction(button.icon(), button.text())
                action.setToolTip(button.toolTip() or button.text())
                action.triggered.connect(button.click)
                button.installEventFilter(self)
                button.setProperty("home_action", action)
                action.setEnabled(button.isEnabled())
            group.layout().insertWidget(0, toolbar)
            box.hide()
        for box in self.findChildren(QtWidgets.QDialogButtonBox):
            close = box.button(QtWidgets.QDialogButtonBox.StandardButton.Close)
            if close is not None:
                close.setText("Quitter")
        place_initial_window(self)
        header = self.jobs_table.horizontalHeader()
        header.setMinimumSectionSize(35)
        width = max(200, self.width() - 36)
        for column, fraction in enumerate((0.25, 0.20, 0.25, 0.22, 0.08)):
            header.resizeSection(column, max(35, int(width * fraction)))

    def add_home_action(self, menu, text, icon_name, signal, shortcut=None):
        icon = QtGui.QIcon.fromTheme(icon_name)
        if icon.isNull():
            icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon)
        action = QtGui.QAction(icon, text, self)
        menu.addAction(action)
        if shortcut:
            action.setShortcut(QtGui.QKeySequence(shortcut))
        action.triggered.connect(lambda checked=False: signal.emit())
        return action

    def sync_action_labels(self):
        for button in (self.start_button, self.finish_current_button, self.defer_button):
            for name in ("home_action", "home_menu_action"):
                action = button.property(name)
                if action is not None:
                    action.setText(button.text())
                    action.setToolTip(button.toolTip() or button.text())

    def update_start_button(self):
        super().update_start_button()
        self.sync_action_labels()

    def update_finish_current_button(self):
        super().update_finish_current_button()
        self.sync_action_labels()

    def update_remove_button(self):
        super().update_remove_button()
        self.sync_action_labels()

    def eventFilter(self, watched, event):
        if event.type() == QtCore.QEvent.Type.EnabledChange:
            for name in ("home_action", "home_menu_action"):
                action = watched.property(name)
                if action is not None:
                    action.setEnabled(watched.isEnabled())
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_timer.start()

    def hideEvent(self, event):
        self.refresh_timer.stop()
        super().hideEvent(event)

    def set_running(self, running):
        super().set_running(running)
        if self.isVisible():
            self.refresh_timer.start()

    def reject(self):
        if self.running:
            QtWidgets.QMessageBox.information(
                self, "File en cours", "Arrête la file ou attends sa fin avant de quitter video_encoder.")
            return
        super().reject()

    def closeEvent(self, event):
        if self.running:
            QtWidgets.QMessageBox.information(
                self, "File en cours", "Arrête la file ou attends sa fin avant de quitter video_encoder.")
            event.ignore()
            return
        super().closeEvent(event)
