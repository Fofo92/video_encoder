import hashlib
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

from PySide6 import QtCore, QtWidgets

from .vidb_review_completion import watch_completion


_profiles = {}


def trace_vidb(message):
    if os.environ.get("VIDEO_ENCODER_VIDB_DEBUG") == "1":
        print(f"[vidb-window {time.monotonic():.3f}] {message}", file=sys.stderr, flush=True)


class VidbWindowEvents(QtCore.QObject):
    def eventFilter(self, watched, event):
        types = {QtCore.QEvent.Type.Show: "show", QtCore.QEvent.Type.Hide: "hide",
                 QtCore.QEvent.Type.Close: "close", QtCore.QEvent.Type.DeferredDelete: "delete"}
        if event.type() in types:
            trace_vidb("modal event=" + types[event.type()])
        if event.type() == QtCore.QEvent.Type.KeyPress and event.key() in (QtCore.Qt.Key.Key_Escape,
                                                                          QtCore.Qt.Key.Key_Return,
                                                                          QtCore.Qt.Key.Key_Enter):
            trace_vidb("modal navigation-key=" + str(event.key()))
        return super().eventFilter(watched, event)


def profile_key(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Lien vidb HTTPS requis")
    origin = f"https://{parsed.hostname.lower()}:{parsed.port or 443}"
    return hashlib.sha256(origin.encode()).hexdigest()[:16]


def build_vidb_browser(parent, url):
    """The ordinary vidb login is isolated from the bridge's bearer secret."""
    key = profile_key(url)
    try:
        from PySide6 import QtWebEngineCore, QtWebEngineWidgets
    except ImportError:
        label = QtWidgets.QLabel(
            "La fenêtre vidb intégrée nécessite le composant Qt WebEngine.\n\n"
            "Sur Zeus : sudo apt install python3-pyside6.qtwebenginewidgets\n\n"
            "Relance ensuite video_encoder. Aucun onglet externe n’a été ouvert.")
        label.setWordWrap(True)
        return label
    if key not in _profiles:
        data_root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
        directory = data_root / "video_encoder" / "vidb-browser" / key
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        directory.chmod(0o700)
        profile = QtWebEngineCore.QWebEngineProfile(f"video-encoder-vidb-{key}", QtWidgets.QApplication.instance())
        profile.setPersistentStoragePath(str(directory))
        profile.setHttpCacheType(QtWebEngineCore.QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(QtWebEngineCore.QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        _profiles[key] = profile
    view = QtWebEngineWidgets.QWebEngineView(parent)
    page = QtWebEngineCore.QWebEnginePage(_profiles[key], view)
    view.setPage(page)
    # Links requesting a new window reuse this view instead of creating tabs.
    page.newWindowRequested.connect(lambda request: request.openIn(page))
    view.setUrl(QtCore.QUrl(url))
    return view


def size_vidb_dialog(dialog):
    screen = dialog.screen()
    geometry = screen.availableGeometry() if screen is not None else None
    dialog.resize(min(1100, int(geometry.width() * .9)) if geometry else 1000,
                  min(820, int(geometry.height() * .9)) if geometry else 750)


def open_vidb_modal(parent, url, require_confirmation=False):
    dialog = QtWidgets.QDialog(parent)
    dialog.setWindowTitle("Identification de l’œuvre dans vidb")
    observer = VidbWindowEvents(dialog)
    if os.environ.get("VIDEO_ENCODER_VIDB_DEBUG") == "1":
        dialog.installEventFilter(observer)
    dialog.finished.connect(lambda code: trace_vidb(f"modal finished={code}"))
    dialog.destroyed.connect(lambda *_args: trace_vidb("modal destroyed"))
    if parent is not None:
        parent.destroyed.connect(lambda *_args: trace_vidb("editor parent destroyed"))
    dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
    layout = QtWidgets.QVBoxLayout(dialog)
    status = QtWidgets.QLabel("Chargement de vidb…", dialog)
    status.setWordWrap(True)
    layout.addWidget(status)
    browser = None
    try:
        trace_vidb("building browser")
        browser = build_vidb_browser(dialog, url)
        trace_vidb("browser type=" + type(browser).__name__)
        layout.addWidget(browser, stretch=1)

        def completed(_record_id):
            trace_vidb("manual form confirmed")
            status.setText("Identification validée. Retour au montage…")
            browser.hide()
            QtCore.QTimer.singleShot(0, dialog.accept)

        watch_completion(browser, url, completed)
        if hasattr(browser, "loadFinished"):
            browser.loadFinished.connect(lambda ok: trace_vidb(f"page loaded={ok}"))
            browser.loadFinished.connect(lambda ok: status.setText(
                "" if ok else "La page vidb n’a pas pu être chargée. Vérifie la connexion puis réessaie."))
        else:
            status.setText("")
        if hasattr(browser, "page"):
            browser.page().renderProcessTerminated.connect(lambda *_args: status.setText(
                "Le navigateur intégré s’est arrêté. Ferme cette fenêtre puis réessaie l’identification."))
    except (OSError, ValueError, RuntimeError, ImportError, AttributeError) as error:
        status.setText(f"Impossible d’ouvrir le navigateur vidb ({type(error).__name__}). "
                       "Le montage reste ouvert. Vérifie l’installation de Qt WebEngine puis réessaie.")
    buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Close)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    size_vidb_dialog(dialog)
    trace_vidb("entering modal event loop")
    result = dialog.exec()
    trace_vidb(f"modal returned={result}")
    if require_confirmation:
        return browser is not None and result == QtWidgets.QDialog.DialogCode.Accepted
    return browser is not None
