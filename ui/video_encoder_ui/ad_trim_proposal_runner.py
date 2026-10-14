import json
import tempfile
from pathlib import Path

from PySide6 import QtCore

from .trim_project_file_reader import TrimProjectFileReader


class AdTrimProposalRunner(QtCore.QObject):
    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QtCore.QProcess(self)
        self.process.finished.connect(self.finish)
        self.process.errorOccurred.connect(self.process_error)
        self.directory = None

    def start(self, report, source, first, last):
        if self.directory is not None:
            raise RuntimeError("Une proposition est déjà en cours.")
        self.directory = tempfile.TemporaryDirectory(prefix="video-encoder-ad-proposal-")
        self.project = Path(self.directory.name) / "proposal.json"
        script = Path(__file__).resolve().parents[2] / "script" / "propose_ad_trim.rb"
        self.process.start("ruby", [
            str(script), "--report", str(report), "--output", str(self.project),
            "--expected-source", str(source),
            "--start-frame", str(first), "--end-frame", str(last),
        ])

    def clean_up(self):
        if self.directory is not None:
            self.directory.cleanup()
            self.directory = None

    def cancel(self):
        if self.directory is None:
            return
        self.clean_up()
        self.process.terminate()
        if not self.process.waitForFinished(1000):
            self.process.kill()
            self.process.waitForFinished(1000)

    def process_error(self, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart and self.directory is not None:
            message = self.process.errorString()
            self.clean_up()
            self.failed.emit(message)

    def finish(self, exit_code, exit_status):
        if self.directory is None:
            return
        stderr = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        stdout = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        try:
            if exit_code != 0 or exit_status != QtCore.QProcess.ExitStatus.NormalExit:
                raise ValueError(stderr.strip() or "La génération de la proposition a échoué.")
            summary = json.loads(stdout)
            session = TrimProjectFileReader().load(self.project)
            result = {"session": session, "summary": summary}
        except (OSError, ValueError, KeyError, TypeError) as error:
            self.clean_up()
            self.failed.emit(str(error))
            return
        self.clean_up()
        self.succeeded.emit(result)
