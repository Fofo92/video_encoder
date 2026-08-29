import os
import signal
from pathlib import Path
from PySide6 import QtCore
from .mlt_progress_parser import MltProgressParser
from .export_event_parser import ExportEventParser

class TrimProjectExporter(QtCore.QObject):
    status_changed = QtCore.Signal(str)
    output_received = QtCore.Signal(str)
    progress_changed = QtCore.Signal(int)
    stage_changed = QtCore.Signal(object)
    succeeded = QtCore.Signal(str)
    failed = QtCore.Signal(str)
    succeeded = QtCore.Signal(str)
    failed = QtCore.Signal(str)

    def __init__(self, executable=None):
        super().__init__()

        project_directory = (
            Path(__file__).resolve().parents[2]
        )

        if executable is None:
            executable = (
                project_directory
                / "bin"
                / "video_encoder"
            )

        self.executable = Path(executable)
        self.ccextractor_executable = (
            project_directory
            / "bin"
            / "video_encoder_ccextractor"
        )

        self.output_path = None
        self.standard_error = ""
        self.progress_parser = MltProgressParser()
        self.event_parser = ExportEventParser()
        self.completed = False
        self.cancel_requested = False

        self.process = QtCore.QProcess(self)

        unix_parameters = (
            QtCore.QProcess.UnixProcessParameters()
        )
        unix_parameters.flags = (
            QtCore.QProcess.UnixProcessFlag.CreateNewSession
        )
        self.process.setUnixProcessParameters(
            unix_parameters
        )

        self.process.setProcessChannelMode(
            QtCore.QProcess.ProcessChannelMode.SeparateChannels
        )
        self.process.readyReadStandardOutput.connect(
            self.read_standard_output
        )
        self.process.readyReadStandardError.connect(
            self.read_standard_error
        )
        self.process.finished.connect(
            self.process_finished
        )
        self.process.errorOccurred.connect(
            self.process_error
        )

    @property
    def is_running(self):
        return (
            self.process.state()
            != QtCore.QProcess.ProcessState.NotRunning
        )

    def start(self, project_path, output_path):
        if self.is_running:
            raise RuntimeError(
                "an export is already running"
            )

        self.output_path = Path(output_path)
        self.standard_error = ""
        self.progress_parser = MltProgressParser()
        self.event_parser = ExportEventParser()
        self.completed = False
        self.cancel_requested = False

        environment = (
            QtCore.QProcessEnvironment.systemEnvironment()
        )

        if not environment.contains(
            "CCEXTRACTOR_EXECUTABLE"
        ):
            environment.insert(
                "CCEXTRACTOR_EXECUTABLE",
                str(self.ccextractor_executable)
            )

        self.process.setProcessEnvironment(environment)
        self.process.setProgram(
            str(self.executable)
        )
        self.process.setArguments(
            [
                "export",
                str(project_path),
                "--output",
                str(self.output_path)
            ]
        )

        self.status_changed.emit("running")
        self.process.start()

    def read_standard_output(self):
        output = bytes(
            self.process.readAllStandardOutput()
        ).decode(errors="replace")

        if not output:
            return

        events, diagnostics = (
            self.event_parser.feed(output)
        )

        self.record_event_output(
            events,
            diagnostics
        )

    def record_event_output(
        self,
        events,
        diagnostics
    ):
        for event in events:
            self.stage_changed.emit(event)

        if diagnostics:
            self.output_received.emit(
                "\n".join(diagnostics)
                + "\n"
            )

    def read_standard_error(self):
        output = bytes(
            self.process.readAllStandardError()
        ).decode(errors="replace")

        if not output:
            return

        percentages, diagnostics = (
            self.progress_parser.feed(output)
        )

        self.record_progress_output(
            percentages,
            diagnostics
        )
        self.output_received.emit(output)

    def record_progress_output(
        self,
        percentages,
        diagnostics
    ):
        for percentage in percentages:
            self.progress_changed.emit(
                percentage
            )

        if diagnostics:
            self.standard_error += (
                "\n".join(diagnostics)
                + "\n"
            )

    def cancel(self, timeout=3_000):
        if not self.is_running:
            return True

        self.cancel_requested = True

        if (
            self.process.state()
            == QtCore.QProcess.ProcessState.Starting
        ):
            self.process.waitForStarted(1_000)

        process_identifier = int(
            self.process.processId()
        )

        if process_identifier <= 0:
            self.process.kill()
            return self.process.waitForFinished(
                1_000
            )

        try:
            os.killpg(
                process_identifier,
                signal.SIGTERM
            )
        except ProcessLookupError:
            pass

        if self.process.waitForFinished(timeout):
            return True

        try:
            os.killpg(
                process_identifier,
                signal.SIGKILL
            )
        except ProcessLookupError:
            pass

        return self.process.waitForFinished(1_000)

    def process_finished(self, exit_code, exit_status):
        self.read_standard_output()
        self.read_standard_error()

        events, output_diagnostics = (
            self.event_parser.finish()
        )
        self.record_event_output(
            events,
            output_diagnostics
        )

        percentages, diagnostics = (
            self.progress_parser.finish()
        )
        self.record_progress_output(
            percentages,
            diagnostics
        )

        if self.cancel_requested:
            self.completed = True
            self.status_changed.emit("cancelled")
            return

        if (
            exit_status
            == QtCore.QProcess.ExitStatus.NormalExit
            and exit_code == 0
        ):
            self.completed = True
            self.status_changed.emit("succeeded")
            self.succeeded.emit(
                str(self.output_path)
            )
            return

        self.report_failure(
            self.standard_error.strip()
            or f"export failed (exit {exit_code})"
        )

    def process_error(self, error):
        if (
            error
            != QtCore.QProcess.ProcessError.FailedToStart
        ):
            return

        self.report_failure(
            self.process.errorString()
        )

    def report_failure(self, message):
        if self.completed:
            return

        self.completed = True
        self.status_changed.emit("failed")
        self.failed.emit(message)

