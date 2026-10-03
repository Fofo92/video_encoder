import json
import os
import signal
import tempfile
import uuid
from pathlib import Path
from PySide6 import QtCore
from .mlt_progress_parser import MltProgressParser


DEFAULT_INHIBITOR_EXECUTABLE = Path(
    "/usr/bin/systemd-inhibit"
)
DEFAULT_SESSION_EXECUTABLE = Path(
    "/usr/bin/setsid"
)

class TrimExportQueueRunner(QtCore.QObject):
    EXPORT_EVENT_PREFIX = "VIDEO_ENCODER_EXPORT_EVENT "

    status_changed = QtCore.Signal(str)
    output_received = QtCore.Signal(str)
    progress_changed = QtCore.Signal(object)
    percentage_changed = QtCore.Signal(int)
    succeeded = QtCore.Signal()
    interrupted = QtCore.Signal()
    stopped = QtCore.Signal()
    failed = QtCore.Signal(str)

    def __init__(
        self,
        executable=None,
        inhibitor_executable=None,
        session_executable=None,
        ccextractor_executable=None,
        stop_after_current_path=None,
    ):
        super().__init__()

        project_directory = (
            Path(__file__).resolve().parents[2]
        )
        uses_default_executable = (
            executable is None
        )

        if executable is None:
            executable = (
                project_directory
                / "bin"
                / "video_encoder"
            )

        if ccextractor_executable is None:
            ccextractor_executable = (
                project_directory
                / "bin"
                / "video_encoder_ccextractor"
            )

        if (
            inhibitor_executable is None
            and uses_default_executable
            and DEFAULT_INHIBITOR_EXECUTABLE.is_file()
        ):
            inhibitor_executable = (
                DEFAULT_INHIBITOR_EXECUTABLE
            )

        if (
            session_executable is None
            and uses_default_executable
            and DEFAULT_SESSION_EXECUTABLE.is_file()
        ):
            session_executable = (
                DEFAULT_SESSION_EXECUTABLE
            )

        self.executable = Path(executable)
        self.ccextractor_executable = Path(
            ccextractor_executable
        )
        self.inhibitor_executable = (
            Path(inhibitor_executable)
            if inhibitor_executable is not None
            else None
        )
        self.progress_parser = MltProgressParser()

        self.session_executable = (
            Path(session_executable)
            if session_executable is not None
            else None
        )

        if stop_after_current_path is None:
            stop_after_current_path = (
                Path(tempfile.gettempdir())
                / (
                    "video-encoder-stop-after-current-"
                    f"{uuid.uuid4().hex}"
                )
            )

        self.stop_after_current_path = Path(
            stop_after_current_path
        )

        self.standard_error = ""
        self.completed = False
        self.stop_requested = False
        self.finish_current_requested = False

        self.process = QtCore.QProcess(self)
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

    def start(self):
        if self.is_running:
            raise RuntimeError(
                "the trim export queue is already running"
            )

        self.standard_error = ""
        self.completed = False
        self.stop_requested = False
        self.finish_current_requested = False
        self.progress_parser = MltProgressParser()
        self.remove_stop_after_current_marker()

        environment = (
            QtCore.QProcessEnvironment.systemEnvironment()
        )
        environment.insert(
            "CCEXTRACTOR_EXECUTABLE",
            str(self.ccextractor_executable),
        )
        environment.insert(
            "VIDEO_ENCODER_STOP_AFTER_CURRENT_FILE",
            str(self.stop_after_current_path),
        )
        self.process.setProcessEnvironment(
            environment
        )

        program = self.executable
        arguments = [
            "run-trim-exports",
            "--once",
        ]

        if self.inhibitor_executable is not None:
            arguments = [
                "--what=sleep",
                "--who=video_encoder",
                "--why=File d’export video_encoder en cours",
                "--mode=block",
                str(program),
                *arguments,
            ]
            program = self.inhibitor_executable

        if self.session_executable is not None:
            arguments = [
                str(program),
                *arguments,
            ]
            program = self.session_executable

        self.process.setProgram(str(program))
        self.process.setArguments(arguments)

        self.status_changed.emit("running")
        self.process.start()

    def stop(self):
        if not self.is_running:
            raise RuntimeError(
                "the trim export queue is not running"
            )

        if self.session_executable is None:
            raise RuntimeError(
                "the trim export queue has no "
                "dedicated process session"
            )

        process_id = int(self.process.processId())

        if process_id <= 0:
            raise RuntimeError(
                "the trim export queue has not started"
            )

        try:
            os.killpg(
                process_id,
                signal.SIGINT,
            )
        except OSError as error:
            raise RuntimeError(
                "could not interrupt the trim export queue"
            ) from error

        self.stop_requested = True

    def finish_current(self):
        if not self.is_running:
            raise RuntimeError(
                "the trim export queue is not running"
            )

        try:
            self.stop_after_current_path.touch(
                exist_ok=True
            )
        except OSError as error:
            raise RuntimeError(
                "could not request a stop after "
                "the current trim export"
            ) from error

        self.finish_current_requested = True

    def read_standard_output(self):
        output = bytes(
            self.process.readAllStandardOutput()
        ).decode(errors="replace")

        if not output:
            return

        self.output_received.emit(output)

        for line in output.splitlines():
            if not line.startswith(
                self.EXPORT_EVENT_PREFIX
            ):
                continue

            payload = line[
                len(self.EXPORT_EVENT_PREFIX):
            ]

            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "warning":
                continue

            self.progress_changed.emit(event)

    def read_standard_error(self):
        output = bytes(
            self.process.readAllStandardError()
        ).decode(errors="replace")

        if not output:
            return

        percentages, _diagnostics = (
            self.progress_parser.feed(output)
        )

        for percentage in percentages:
            self.percentage_changed.emit(
                percentage
            )

        self.standard_error += output
        self.output_received.emit(output)

    def process_finished(
        self,
        exit_code,
        exit_status,
    ):
        self.read_standard_output()
        self.read_standard_error()

        if self.stop_requested:
            self.completed = True
            self.remove_stop_after_current_marker()
            self.status_changed.emit("interrupted")
            self.interrupted.emit()
            return

        if (
            exit_status
            == QtCore.QProcess.ExitStatus.NormalExit
            and exit_code == 0
        ):
            self.completed = True

            if self.finish_current_requested:
                self.remove_stop_after_current_marker()
                self.status_changed.emit("stopped")
                self.stopped.emit()
                return

            self.remove_stop_after_current_marker()
            self.status_changed.emit("succeeded")
            self.succeeded.emit()
            return

        self.report_failure(
            self.standard_error.strip()
            or (
                "trim export queue failed "
                f"(exit {exit_code})"
            )
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
        self.remove_stop_after_current_marker()
        self.status_changed.emit("failed")
        self.failed.emit(message)

    def remove_stop_after_current_marker(self):
        try:
            self.stop_after_current_path.unlink(
                missing_ok=True
            )
        except OSError as error:
            raise RuntimeError(
                "could not clear the stop-after-current "
                "request"
            ) from error
