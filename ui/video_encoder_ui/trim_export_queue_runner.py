from pathlib import Path

from PySide6 import QtCore


DEFAULT_INHIBITOR_EXECUTABLE = Path(
    "/usr/bin/systemd-inhibit"
)


class TrimExportQueueRunner(QtCore.QObject):
    status_changed = QtCore.Signal(str)
    output_received = QtCore.Signal(str)
    succeeded = QtCore.Signal()
    failed = QtCore.Signal(str)

    def __init__(
        self,
        executable=None,
        inhibitor_executable=None,
        ccextractor_executable=None,
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

        self.executable = Path(executable)
        self.ccextractor_executable = Path(
            ccextractor_executable
        )
        self.inhibitor_executable = (
            Path(inhibitor_executable)
            if inhibitor_executable is not None
            else None
        )

        self.standard_error = ""
        self.completed = False

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

        environment = (
            QtCore.QProcessEnvironment.systemEnvironment()
        )
        environment.insert(
            "CCEXTRACTOR_EXECUTABLE",
            str(self.ccextractor_executable),
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

        self.process.setProgram(str(program))
        self.process.setArguments(arguments)

        self.status_changed.emit("running")
        self.process.start()

    def read_standard_output(self):
        output = bytes(
            self.process.readAllStandardOutput()
        ).decode(errors="replace")

        if output:
            self.output_received.emit(output)

    def read_standard_error(self):
        output = bytes(
            self.process.readAllStandardError()
        ).decode(errors="replace")

        if not output:
            return

        self.standard_error += output
        self.output_received.emit(output)

    def process_finished(
        self,
        exit_code,
        exit_status,
    ):
        self.read_standard_output()
        self.read_standard_error()

        if (
            exit_status
            == QtCore.QProcess.ExitStatus.NormalExit
            and exit_code == 0
        ):
            self.completed = True
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
        self.status_changed.emit("failed")
        self.failed.emit(message)
