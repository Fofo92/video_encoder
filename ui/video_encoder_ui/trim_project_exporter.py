from pathlib import Path

from PySide6 import QtCore


class TrimProjectExporter(QtCore.QObject):
    status_changed = QtCore.Signal(str)
    output_received = QtCore.Signal(str)
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

    def start(self, project_path, output_path):
        if self.is_running:
            raise RuntimeError(
                "an export is already running"
            )

        self.output_path = Path(output_path)
        self.standard_error = ""
        self.completed = False

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

        if output:
            self.output_received.emit(output)

    def read_standard_error(self):
        output = bytes(
            self.process.readAllStandardError()
        ).decode(errors="replace")

        if output:
            self.standard_error += output
            self.output_received.emit(output)

    def process_finished(self, exit_code, exit_status):
        self.read_standard_output()
        self.read_standard_error()

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

