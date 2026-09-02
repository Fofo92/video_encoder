import subprocess
from pathlib import Path


class TrimExportQueueError(RuntimeError):
    pass


class TrimExportQueueClient:
    def __init__(
        self,
        executable=None,
        runner=None,
    ):
        if executable is None:
            executable = (
                Path(__file__).resolve().parents[2]
                / "bin"
                / "video_encoder"
            )

        self.executable = Path(executable)
        self.runner = runner or subprocess.run

    def enqueue(
        self,
        project_path,
        output_path,
    ):
        result = self.runner(
            [
                str(self.executable),
                "enqueue-trim-export",
                str(project_path),
                "--output",
                str(output_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise TrimExportQueueError(
                self.error_message(result)
            )

        return result.stdout.strip()

    @staticmethod
    def error_message(result):
        message = result.stderr.strip()

        if message:
            return message

        message = result.stdout.strip()

        if message:
            return message

        return "trim export enqueue failed"
