"""Run the frozen 6ter pipeline without exporting media."""

import json
from pathlib import Path

from PySide6 import QtCore
from .ad_detection_result import empty_detection_report


class AdAnalysisRunner(QtCore.QObject):
    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)
    progress = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.read_progress)
        self.process.finished.connect(self.finish)
        self.process.errorOccurred.connect(self.process_error)
        self.workspace = None
        self.source = None

    def start(self, source, workspace, first, last):
        if self.workspace is not None:
            raise RuntimeError("Une analyse est déjà en cours.")
        source = Path(source).resolve(strict=True)
        workspace = Path(workspace).expanduser().resolve()
        if not source.is_file() or not 0 <= first < last:
            raise ValueError("Source ou bornes IN/OUT invalides.")
        if workspace.exists():
            raise FileExistsError("Espace d'analyse existant : choisir un nouveau dossier.")
        script = Path(__file__).resolve().parents[2] / "script" / "prepare_ad_trim.rb"
        self.workspace, self.source = workspace, source
        self.process.start("ruby", [
            str(script), "--source", str(source), "--workspace", str(workspace),
            "--start-frame", str(first), "--end-frame", str(last),
        ])

    def read_progress(self):
        message = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if message.strip():
            self.progress.emit(message.strip())

    def reset(self):
        self.workspace = None
        self.source = None

    def cancel(self):
        if self.workspace is None:
            return
        self.reset()
        self.process.terminate()
        if not self.process.waitForFinished(1500):
            self.process.kill()
            self.process.waitForFinished(1500)

    def process_error(self, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart and self.workspace is not None:
            message = self.process.errorString()
            self.reset()
            self.failed.emit(message)

    def finish(self, exit_code, exit_status):
        if self.workspace is None:
            return
        workspace = self.workspace
        source = self.source
        self.read_progress()
        self.reset()
        empty_report = empty_detection_report(workspace, source)
        if empty_report is not None and exit_status == QtCore.QProcess.ExitStatus.NormalExit:
            self.succeeded.emit({"status": "no_candidates", "report": empty_report, "workspace": workspace})
            return
        if exit_code != 0 or exit_status != QtCore.QProcess.ExitStatus.NormalExit:
            self.failed.emit(f"Analyse interrompue ou échouée. Diagnostics conservés : {workspace}")
            return
        try:
            report = workspace / "boundaries" / "boundary-hypotheses.json"
            project = workspace / "proposal.json"
            if not report.is_file() or not project.is_file():
                raise ValueError("Résultats incomplets.")
            summary = json.loads(project.read_text(encoding="utf-8"))
            if summary.get("format") != "video_encoder.trim_project":
                raise ValueError("Projet généré invalide.")
        except (OSError, ValueError) as error:
            self.failed.emit(str(error))
            return
        self.succeeded.emit({"report": report, "project": project, "workspace": workspace})
