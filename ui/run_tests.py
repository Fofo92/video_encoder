"""Run the UI suite with one QApplication and explicit Qt widget cleanup."""
import gc
import os
from pathlib import Path
import unittest


def main():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from PySide6 import QtCore, QtWidgets
    except ModuleNotFoundError as error:
        if error.name != "PySide6":
            raise
        QtCore = QtWidgets = None

    application = None
    if QtWidgets is not None:
        application = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        application.setQuitOnLastWindowClosed(False)
    try:
        suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent / "tests"), pattern="test_*.py")
        result = unittest.TextTestRunner().run(suite)
        return 0 if result.wasSuccessful() else 1
    finally:
        if application is not None:
            # Destroy native widget trees while QApplication and its dispatcher
            # are still alive; processEvents() alone does not drain DeferredDelete.
            for widget in application.topLevelWidgets():
                widget.close()
                widget.deleteLater()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            gc.collect()
            QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


if __name__ == "__main__":
    raise SystemExit(main())
