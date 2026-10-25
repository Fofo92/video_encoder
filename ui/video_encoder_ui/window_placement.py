from PySide6 import QtGui, QtWidgets


def place_initial_window(window):
    """Use the upper left third of the screen containing the pointer."""
    if not isinstance(window, QtWidgets.QWidget):
        return
    screen = QtGui.QGuiApplication.screenAt(QtGui.QCursor.pos())
    screen = screen or window.screen() or QtGui.QGuiApplication.primaryScreen()
    if screen is None:
        return
    area = screen.availableGeometry()
    window.resize(max(1, area.width() // 3), max(1, area.height() // 2))
    window.move(area.topLeft())
