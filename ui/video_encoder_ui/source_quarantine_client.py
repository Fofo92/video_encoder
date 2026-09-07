import subprocess
from pathlib import Path


class SourceQuarantineError(RuntimeError):
    pass


class SourceQuarantineClient:
    def __init__(self, executable=None, runner=None):
        if executable is None:
            executable = (
                Path(__file__).resolve().parents[2]
                / "bin"
                / "video_encoder"
            )

        self.executable = Path(executable)
        self.runner = runner or subprocess.run

    def quarantine(self, source_path):
        result = self.runner(
            [
                str(self.executable),
                "quarantine-source",
                str(source_path),
                "--confirm",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            message = (
                result.stderr.strip()
                or result.stdout.strip()
                or "source quarantine failed"
            )
            raise SourceQuarantineError(message)

        return result.stdout.strip()
