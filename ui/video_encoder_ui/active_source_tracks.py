"""Display the tracks of the active source without blocking the montage."""
import json

from PySide6 import QtCore, QtWidgets

from .media_inspection_client import MediaInspectionError


def track_lines(inspection):
    for label, key in (("Vidéo", "video_tracks"), ("Audio", "audio_tracks"),
                       ("Sous-titres", "subtitle_tracks")):
        for track in inspection.get(key, []):
            attributes = [track.get("codec") or "codec inconnu"]
            if key == "video_tracks" and track.get("width") and track.get("height"):
                attributes.append(f"{track['width']}×{track['height']}")
                rate = track.get("frame_rate") or {}
                if rate.get("numerator") and rate.get("denominator"):
                    attributes.append(f"{rate['numerator'] / rate['denominator']:g} i/s")
            if key != "video_tracks":
                attributes.append(track.get("language") or "langue inconnue")
            for flag, description in (("default", "par défaut"), ("forced", "forcés"),
                                      ("visual_impaired", "audiodescription"),
                                      ("hearing_impaired", "malentendants")):
                if track.get(flag):
                    attributes.append(description)
            yield f"{label} {track['index']} · " + " · ".join(attributes)


class ActiveSourceTracks(QtWidgets.QGroupBox):
    def __init__(self, client):
        super().__init__("Pistes de la source active")
        self.client = client
        self.source = None
        self.process = None
        self.details = QtWidgets.QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setMinimumHeight(165)
        self.details.setAccessibleName(self.title())
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.addWidget(self.details)
        self.setMaximumHeight(220)

    def show_source(self, source):
        if source == self.source:
            return
        self.source = source
        self.stop_inspection()
        if source is None:
            self.details.clear()
            return

        self.details.setPlainText("Inspection des pistes…")
        process = QtCore.QProcess(self)
        self.process = process
        process.finished.connect(lambda code, _status: self.finish(process, code))
        process.errorOccurred.connect(lambda error: self.process_error(process, error))
        process.start(str(self.client.executable), ["inspect-media", str(source)])

    def stop_inspection(self):
        process = self.process
        if process is None:
            return

        self.process = None
        process.blockSignals(True)
        if process.state() != QtCore.QProcess.ProcessState.NotRunning:
            process.kill()
            process.waitForFinished(1000)
        process.deleteLater()

    def process_error(self, process, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart:
            self.finish(process, -1)

    def finish(self, process, code):
        if process is not self.process:
            return
        self.process = None
        process.deleteLater()
        try:
            if code != 0:
                raise MediaInspectionError("Inspection des pistes indisponible.")
            document = json.loads(bytes(process.readAllStandardOutput()))
            self.client.validate(document)
            lines = list(track_lines(document["source"]["inspection"]))
        except (MediaInspectionError, ValueError, TypeError, KeyError):
            self.details.setPlainText("Inspection des pistes indisponible.")
            return
        self.details.setPlainText("\n".join(lines) or "Aucune piste détectée.")
