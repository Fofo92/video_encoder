from pathlib import Path

from PySide6 import QtGui, QtWidgets


SOURCE_COLORS = (
    "#3daee9",
    "#e6a23c",
    "#67c23a",
)


class SourceInformationDialog(QtWidgets.QDialog):
    def __init__(self, sources, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "Informations sur les sources"
        )
        self.resize(700, 480)

        layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget(self)
        layout.addWidget(self.tabs)

        for index, source in enumerate(sources):
            self.add_source_tab(
                source,
                index
            )

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_source_tab(self, source, index):
        path = Path(source["path"])
        contents = QtWidgets.QPlainTextEdit(self)
        contents.setReadOnly(True)
        contents.setPlainText(
            self.source_text(source)
        )

        tab_index = self.tabs.addTab(
            contents,
            path.name
        )
        self.tabs.tabBar().setTabTextColor(
            tab_index,
            QtGui.QColor(
                SOURCE_COLORS[
                    index % len(SOURCE_COLORS)
                ]
            )
        )

    def source_text(self, source):
        inspection = source["inspection"]
        lines = [
            f"Fichier : {source['path']}",
            (
                "Inspection : "
                f"{inspection.get('inspected_at', 'Non datée')}"
            ),
            (
                "Durée : "
                f"{self.format_duration(inspection.get('duration'))}"
            ),
            (
                "Taille : "
                f"{self.format_size(inspection.get('size_bytes'))}"
            ),
            "",
            "Vidéo",
        ]

        lines.extend(
            self.video_track_text(track)
            for track in inspection.get(
                "video_tracks",
                []
            )
        )

        lines.append("")
        lines.append("Audio")
        lines.extend(
            self.audio_track_text(track)
            for track in inspection.get(
                "audio_tracks",
                []
            )
        )

        lines.append("")
        lines.append("Sous-titres")
        lines.extend(
            self.subtitle_track_text(track)
            for track in inspection.get(
                "subtitle_tracks",
                []
            )
        )

        return "\n".join(lines)

    def video_track_text(self, track):
        frame_rate = track.get("frame_rate")
        rate = "cadence inconnue"

        if frame_rate:
            numerator = frame_rate["numerator"]
            denominator = frame_rate["denominator"]
            rate = f"{numerator / denominator:g} i/s"

        return (
            f"  Piste {track['index']} — "
            f"{track.get('codec') or 'codec inconnu'} — "
            f"{track.get('width', '?')}×"
            f"{track.get('height', '?')} — "
            f"{rate}"
        )

    def audio_track_text(self, track):
        details = self.track_details(
            track,
            accessibility_key="visual_impaired",
            accessibility_label="audiodescription",
        )

        return (
            f"  Piste {track['index']} — "
            f"{track.get('codec') or 'codec inconnu'}"
            f"{details}"
        )

    def subtitle_track_text(self, track):
        details = self.track_details(
            track,
            accessibility_key="hearing_impaired",
            accessibility_label="malentendants",
        )

        if track.get("forced"):
            details += " — forcés"

        return (
            f"  Piste {track['index']} — "
            f"{track.get('codec') or 'codec inconnu'}"
            f"{details}"
        )

    @staticmethod
    def track_details(
        track,
        accessibility_key,
        accessibility_label,
    ):
        details = (
            f" — {track.get('language') or 'langue inconnue'}"
        )

        if track.get("default"):
            details += " — par défaut"

        if track.get(accessibility_key):
            details += f" — {accessibility_label}"

        return details

    @staticmethod
    def format_duration(duration):
        if duration is None:
            return "Non disponible"

        hours, remainder = divmod(
            float(duration),
            3600
        )
        minutes, seconds = divmod(
            remainder,
            60
        )

        return (
            f"{int(hours):02d}:"
            f"{int(minutes):02d}:"
            f"{seconds:06.3f}"
        )

    @staticmethod
    def format_size(size_bytes):
        if size_bytes is None:
            return "Non disponible"

        gibibytes = size_bytes / (1024 ** 3)
        return f"{gibibytes:.2f} Gio"
