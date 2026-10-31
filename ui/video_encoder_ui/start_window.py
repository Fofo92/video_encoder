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
    delete_project_requested = QtCore.Signal()
    project_trash_requested = QtCore.Signal()

    def __init__(self):
        super().__init__(jobs=[])
        self.setWindowTitle("video_encoder — Montages")
        self.setWindowModality(QtCore.Qt.WindowModality.NonModal)
        self.menu_bar = QtWidgets.QMenuBar(self)
        self.layout().setMenuBar(self.menu_bar)
        self.exit_menu_bar = QtWidgets.QMenuBar(self.menu_bar)
        self.exit_action = QtGui.QAction("Quitter", self)
        self.exit_action.triggered.connect(self.reject)
        self.exit_menu_bar.addAction(self.exit_action)
        self.menu_bar.setCornerWidget(self.exit_menu_bar, QtCore.Qt.Corner.TopRightCorner)
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
        self.quarantine_policy_action = QtGui.QAction("Suivi de la quarantaine…", self)
        sources.addAction(self.quarantine_policy_action)
        self.quarantine_policy_action.triggered.connect(self.show_quarantine_policy)
        self.open_project_action = self.add_home_action(
            projects, "Ouvrir un projet…", "document-open", self.open_project_requested, "Ctrl+O")
        self.relocate_project_action = self.add_home_action(
            projects, "Déplacer ou renommer un projet et sa vidéo…", "folder-move", self.relocate_requested)
        # One entry point for starting a montage; keep the shared action owned by the window.
        sources.removeAction(self.new_project_action)
        self.delete_project_action = self.add_home_action(
            projects, "Supprimer un projet…", "edit-delete", self.delete_project_requested)
        self.project_trash_action = self.add_home_action(
            projects, "Corbeille des projets…", "user-trash", self.project_trash_requested)
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
            toolbar.setIconSize(QtCore.QSize(16, 16))
            toolbar.setContentsMargins(0, 0, 0, 0)
            row_height = self.jobs_table.verticalHeader().defaultSectionSize()
            group.setFixedHeight(row_height)
            toolbar.setFixedHeight(max(16, row_height - 2))
            toolbar.setStyleSheet(
                "QToolBar { padding: 0px; margin: 0px; spacing: 2px; } "
                "QToolButton { padding: 1px 3px; margin: 0px; }")
            toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            for button in box.buttons():
                action = toolbar.addAction(button.icon(), self.toolbar_label(button))
                action.setToolTip(button.toolTip() or button.text())
                action.triggered.connect(button.click)
                button.installEventFilter(self)
                button.setProperty("home_action", action)
                action.setEnabled(button.isEnabled())
            group.layout().insertWidget(1, toolbar, 1)
            box.hide()
        for box in self.findChildren(QtWidgets.QDialogButtonBox):
            close = box.button(QtWidgets.QDialogButtonBox.StandardButton.Close)
            if close is not None:
                box.hide()
        self.install_main_actions_toolbar()
        self.status_bar = QtWidgets.QStatusBar(self)
        self.status_bar.setSizeGripEnabled(False)
        self.layout().addWidget(self.status_bar)
        self.update_status_bar()
        # Toolbars and the table must not enlarge the requested screen fraction.
        self.layout().setSizeConstraint(QtWidgets.QLayout.SizeConstraint.SetNoConstraint)
        self.setMinimumSize(0, 0)
        place_initial_window(self)
        header = self.jobs_table.horizontalHeader()
        header.setMinimumSectionSize(35)
        width = max(200, self.width() - 36)
        for column, fraction in enumerate((0.25, 0.20, 0.25, 0.22, 0.08)):
            header.resizeSection(column, max(35, int(width * fraction)))

    def install_main_actions_toolbar(self):
        # Keep application actions local even when Plasma exports native menus.
        self.menu_bar.setNativeMenuBar(False)
        self.exit_menu_bar.setNativeMenuBar(False)
        self.main_toolbar = QtWidgets.QToolBar("Actions principales", self)
        self.main_toolbar.setObjectName("home_main_toolbar")
        self.main_toolbar.setMovable(False)
        self.main_toolbar.setContentsMargins(0, 0, 0, 0)
        self.main_toolbar.setStyleSheet("QToolBar { padding: 0px; margin: 0px; }")
        self.main_toolbar.setIconSize(QtCore.QSize(24, 24))
        self.main_toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        for action in (self.new_montage_action, self.open_project_action):
            self.main_toolbar.addAction(action)
        self.main_toolbar.addSeparator()
        for action in (self.relocate_project_action, self.quarantine_action):
            self.main_toolbar.addAction(action)
        labels = ((self.new_montage_action, "Nouveau montage…"),
                  (self.open_project_action, "Ouvrir un projet…"),
                  (self.relocate_project_action, "Déplacer / renommer…"),
                  (self.quarantine_action, "Quarantaine…"))
        for action, label in labels:
            button = self.main_toolbar.widgetForAction(action)
            button.setText(label)
            button.setToolTip(action.text())
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().insertWidget(0, self.main_toolbar)

    def show_quarantine_policy(self):
        from .quarantine_policy_dialog import show_quarantine_policy
        show_quarantine_policy(self)

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
                    action.setText(self.toolbar_label(button) if name == "home_action" else button.text())
                    action.setToolTip(button.toolTip() or button.text())

    @staticmethod
    def toolbar_label(button):
        return {
            "Lancer la file": "Lancer",
            "File en cours…": "Lancer",
            "Lancer uniquement la sélection": "Lancer",
            "Relancer le travail": "Relancer",
            "Interrompre la file": "Interrompre",
            "Supprimer la tâche": "Supprimer",
            "Destination…": "Modifier…",
            "Enchaîner après le montage en cours": "Enchaîner",
            "Suite programmée": "Enchaîner",
        }.get(button.text(), button.text())

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
        self.update_status_bar()
        if self.isVisible():
            self.refresh_timer.start()

    def set_jobs(self, jobs):
        super().set_jobs(jobs)
        self.update_status_bar()

    def update_status_bar(self):
        if getattr(self, "status_bar", None) is None:
            return
        encoding = self.running or any(job.get("status") == "running" for job in self.jobs)
        count = sum(job.get("status") == "queued" for job in self.jobs)
        state = "Encodage en cours" if encoding else "Aucun encodage en cours"
        pending = "tâche en attente" if count == 1 else "tâches en attente"
        self.status_bar.showMessage(f"{state} — {count} {pending}")

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
