import json
import subprocess
from pathlib import Path


class MediaInspectionError(RuntimeError):
    pass


class MediaInspectionClient:
    FORMAT = "video_encoder.media_inspection"
    VERSION = 1

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

    def inspect(self, source_path):
        result = self.runner(
            [
                str(self.executable),
                "inspect-media",
                str(source_path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise MediaInspectionError(
                self.error_message(result)
            )

        try:
            document = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise MediaInspectionError(
                "invalid media inspection response"
            ) from error

        self.validate(document)

        return document["source"]

    def validate(self, document):
        if document.get("format") != self.FORMAT:
            raise MediaInspectionError(
                "unsupported media inspection format"
            )

        if document.get("version") != self.VERSION:
            raise MediaInspectionError(
                "unsupported media inspection version"
            )

        source = document.get("source")

        if not isinstance(source, dict):
            raise MediaInspectionError(
                "media inspection source is required"
            )

        if not isinstance(
            source.get("inspection"),
            dict,
        ):
            raise MediaInspectionError(
                "media inspection data is required"
            )

    @staticmethod
    def error_message(result):
        message = result.stderr.strip()

        if message:
            return message

        message = result.stdout.strip()

        if message:
            return message

        return "media inspection failed"
