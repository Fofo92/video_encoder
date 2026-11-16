"""Deliver browser launches to the existing local application, never to another host."""
from collections import deque
from hashlib import sha256
import os
from pathlib import Path

from PySide6 import QtCore, QtNetwork
from .desktop_instance import other_application_pids


def inbox_name():
    return f"video_encoder-desktop-{os.getuid()}"


def start_inbox(parent, url):
    if url and DesktopInbox.forward(url):
        return None
    if other_application_pids():
        raise OSError("Une autre instance de video_encoder est ouverte. Ferme-la après les encodages, "
                      "puis relance l’application pour activer l’entrée vidb.")
    try:
        return DesktopInbox(parent)
    except OSError:
        # Retry only a startup race, never an uncertain delivery.
        if url and DesktopInbox.forward(url):
            return None
        raise


class DesktopInbox(QtCore.QObject):
    def __init__(self, parent=None, *, name=None):
        super().__init__(parent)
        self.name = name or inbox_name()
        self.handler = None
        self.pending = deque()
        self.busy = False
        self.server = QtNetwork.QLocalServer(self)
        self.server.setSocketOptions(QtNetwork.QLocalServer.SocketOption.UserAccessOption)
        self._instance_lock = self.acquire_instance_lock()
        try:
            self.listen()
            self.server.newConnection.connect(self.accept_connections)
        except BaseException:
            self.server.close()
            self._instance_lock.unlock()
            raise

    def acquire_instance_lock(self):
        runtime = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.StandardLocation.RuntimeLocation)
        directory = Path(runtime or QtCore.QDir.tempPath())
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        digest = sha256(self.name.encode("utf-8")).hexdigest()
        lock = QtCore.QLockFile(str(directory / f"video_encoder-{os.getuid()}-{digest}.lock"))
        # Never expire an active interface's lock merely because encoding takes hours.
        lock.setStaleLockTime(0)
        if not lock.tryLock(0):
            raise OSError("video_encoder est déjà ouvert ou son entrée locale est verrouillée.")
        return lock

    def listen(self):
        # Never touch an address already answering, including older interfaces.
        probe = QtNetwork.QLocalSocket()
        probe.connectToServer(self.name)
        if probe.waitForConnected(250):
            probe.disconnectFromServer()
            raise OSError("video_encoder est déjà ouvert. Utilise sa fenêtre existante.")
        stale = {QtNetwork.QLocalSocket.LocalSocketError.ConnectionRefusedError,
                 QtNetwork.QLocalSocket.LocalSocketError.ServerNotFoundError}
        if probe.error() not in stale:
            raise OSError("Le point d’entrée local de video_encoder est indisponible.")
        if not self.server.listen(self.name):
            QtNetwork.QLocalServer.removeServer(self.name)
            if not self.server.listen(self.name):
                raise OSError("Impossible d’ouvrir le point d’entrée local de video_encoder.")

    @staticmethod
    def forward(url, *, name=None):
        socket = QtNetwork.QLocalSocket()
        socket.connectToServer(name or inbox_name())
        if not socket.waitForConnected(500):
            if socket.error() in {QtNetwork.QLocalSocket.LocalSocketError.ConnectionRefusedError,
                                  QtNetwork.QLocalSocket.LocalSocketError.ServerNotFoundError}:
                return False
            raise OSError("Connexion à video_encoder impossible ; aucune seconde instance n’a été lancée.")
        raw = url.encode("utf-8")
        if len(raw) > 8192 or b"\n" in raw or b"\r" in raw:
            raise ValueError("Lien de préparation invalide.")
        socket.write(raw + b"\n")
        if socket.bytesToWrite() and not socket.waitForBytesWritten(1000):
            raise OSError("La transmission de la demande à video_encoder a échoué.")
        timer = QtCore.QElapsedTimer()
        timer.start()
        while not socket.canReadLine():
            remaining = 1500 - timer.elapsed()
            if remaining <= 0 or (not socket.waitForReadyRead(remaining) and not socket.canReadLine()):
                raise OSError("video_encoder n’a pas confirmé la demande ; aucune seconde instance n’a été lancée.")
        accepted = bytes(socket.readLine()).strip() == b"queued"
        socket.disconnectFromServer()
        if not accepted:
            raise OSError("La demande a été refusée par video_encoder.")
        return True

    def set_handler(self, handler):
        self.handler = handler
        QtCore.QTimer.singleShot(0, self.drain)

    def submit(self, url):
        if len(self.pending) >= 8 or not url.startswith("vidb-encoder://"):
            return False
        self.pending.append(url)
        QtCore.QTimer.singleShot(0, self.drain)
        return True

    def accept_connections(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.setReadBufferSize(8194)
            socket._launch_buffer = bytearray()
            socket._launch_complete = False
            timeout = QtCore.QTimer(socket)
            timeout.setSingleShot(True)
            timeout.timeout.connect(socket.abort)
            timeout.start(5000)
            socket.readyRead.connect(lambda connection=socket: self.read_connection(connection))
            socket.disconnected.connect(socket.deleteLater)
            self.read_connection(socket)

    def read_connection(self, socket):
        if socket._launch_complete:
            return
        socket._launch_buffer.extend(bytes(socket.readAll()))
        raw = socket._launch_buffer
        if len(raw) > 8193:
            socket.abort()
            return
        if b"\n" not in raw:
            return
        socket._launch_complete = True
        try:
            url = bytes(raw).decode("utf-8").rstrip("\n")
            accepted = "\n" not in url and self.submit(url)
        except UnicodeError:
            accepted = False
        socket.write(b"queued\n" if accepted else b"rejected\n")
        socket.disconnectFromServer()

    def drain(self):
        if self.busy or self.handler is None or not self.pending:
            return
        self.busy = True
        try:
            self.handler(self.pending.popleft())
        finally:
            self.busy = False
            if self.pending:
                QtCore.QTimer.singleShot(0, self.drain)

    def close(self):
        try:
            self.server.close()
        finally:
            self._instance_lock.unlock()
