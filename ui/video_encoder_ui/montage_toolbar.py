from PySide6 import QtCore, QtWidgets


def install_montage_toolbar(window):
    """Expose the montage lifecycle through the editor's existing actions."""
    toolbar = window.addToolBar("Cycle du montage")
    toolbar.setObjectName("main_toolbar")
    toolbar.setMovable(False)
    toolbar.setContentsMargins(0, 0, 0, 0)
    toolbar.setStyleSheet("QToolBar { padding: 0px; margin: 0px; }")
    toolbar.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonIconOnly)
    toolbar.setIconSize(QtCore.QSize(24, 24))
    groups = (
        (("new_montage_action", "Nouveau montage (Ctrl+N)"),
         ("save_project_action", "Enregistrer le montage (Ctrl+S)")),
        (("identify_vidb_action", "Identifier l’œuvre dans vidb"),
         ("queue_export_action", "Identifier puis mettre le montage en file (Ctrl+Shift+E)"),
         ("show_export_queue_action", "Suivre la file des montages (Ctrl+Shift+Q)")),
        (("export_project_action", "Encoder le montage immédiatement (Ctrl+E)"),
         ("cancel_export_action", "Interrompre l’encodage immédiat en cours")),
        (("source_information_action", "Consulter les informations des sources"),),
    )
    for position, group in enumerate(groups):
        if position:
            toolbar.addSeparator()
        for name, tooltip in group:
            action = getattr(window, name)
            action.setToolTip(tooltip)
            toolbar.addAction(action)
            button = toolbar.widgetForAction(action)
            button.setAttribute(QtCore.Qt.WidgetAttribute.WA_AlwaysShowToolTips, True)
    toolbar.show()
    return toolbar
