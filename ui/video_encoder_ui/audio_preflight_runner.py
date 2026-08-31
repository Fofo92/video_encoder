import json
import os
import signal
from pathlib import Path
from PySide6 import QtCore


class AudioPreflightRunner(QtCore.QObject):
    status_changed = QtCore.Signal(str)
    succeeded = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, executable=None):
        super().__init__()

        if executable is None:
            executable = (
                Path(__file__).resolve().parents[2]
                / "bin"
                / "video_encoder"
            )

        self.executable = Path(executable)
        self.completed = False

        self.cancel_requested = False

        self.cancel_timer = QtCore.QTimer(self)
        self.cancel_timer.setSingleShot(True)
        self.cancel_timer.setInterval(1_000)
        self.cancel_timer.timeout.connect(self.force_cancel)

        self.process = QtCore.QProcess(self)
        unix_parameters = QtCore.QProcess.UnixProcessParameters()
        unix_parameters.flags = (
            QtCore.QProcess.UnixProcessFlag.CreateNewSession
        )
        self.process.setUnixProcessParameters(unix_parameters)
        self.process.started.connect(self.request_cancellation)
        self.process.setProcessChannelMode(
            QtCore.QProcess.ProcessChannelMode.SeparateChannels
        )
        self.process.finished.connect(self.process_finished)
        self.process.errorOccurred.connect(self.process_error)

    @property
    def is_running(self):
        return (
            self.process.state()
            != QtCore.QProcess.ProcessState.NotRunning
        )

    def start(self, project_path):
        if self.is_running:
            raise RuntimeError(
                "an audio preflight is already running"
            )

        self.completed = False
        self.cancel_requested = False
        self.cancel_timer.stop()
        self.process.setProgram(str(self.executable))
        self.process.setArguments(
            ["preflight-audio", str(project_path)]
        )

        self.status_changed.emit("running")
        self.process.start()

    def cancel(self):
        if not self.is_running:
            return True

        self.cancel_requested = True
        self.request_cancellation()
        return True

    def request_cancellation(self):
        if not self.cancel_requested:
            return

        if (
            self.process.state()
            != QtCore.QProcess.ProcessState.Running
        ):
            return

        self.signal_process_group(signal.SIGTERM)

        if self.is_running and not self.completed:
            self.cancel_timer.start()

    def force_cancel(self):
        if self.cancel_requested and self.is_running:
            self.signal_process_group(signal.SIGKILL)

    def signal_process_group(self, requested_signal):
        process_identifier = int(self.process.processId())

        if process_identifier <= 0:
            return

        try:
            os.killpg(process_identifier, requested_signal)
        except ProcessLookupError:
            pass

    def process_finished(self, exit_code, exit_status):
        if self.completed:
            return

        self.cancel_timer.stop()

        if self.cancel_requested:
            self.completed = True
            self.status_changed.emit("cancelled")
            return

        output = bytes(self.process.readAllStandardOutput())
        diagnostic = bytes(
            self.process.readAllStandardError()
        ).decode(errors="replace").strip()

        if (
            exit_status != QtCore.QProcess.ExitStatus.NormalExit
            or exit_code != 0
        ):
            self.report_failure(
                diagnostic
                or f"audio preflight failed (exit {exit_code})"
            )
            return

        try:
            report = json.loads(output.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            self.report_failure(
                f"invalid audio preflight report: {error}"
            )
            return

        if not self.valid_report(report):
            self.report_failure(
                "unsupported audio preflight report"
            )
            return

        self.completed = True
        self.status_changed.emit("succeeded")
        self.succeeded.emit(report)

    @staticmethod
    def valid_report(report):
        return (
            isinstance(report, dict)
            and type(report.get("version")) is int
            and report["version"] == 1
            and isinstance(report.get("audio_checks"), list)
        )

    def process_error(self, error):
        if error == QtCore.QProcess.ProcessError.FailedToStart:
            self.report_failure(self.process.errorString())

    def report_failure(self, message):
        if self.completed:
            return

        self.cancel_timer.stop()
        self.completed = True
        self.status_changed.emit("failed")
        self.failed.emit(message)
