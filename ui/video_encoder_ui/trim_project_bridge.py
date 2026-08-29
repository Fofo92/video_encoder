import json
import subprocess
from pathlib import Path


class TrimProjectBridgeError(RuntimeError):
    pass


class TrimProjectBridge:
    def __init__(self, executable=None, runner=None):
        if executable is None:
            executable = (
                Path(__file__).resolve().parents[2]
                / "bin"
                / "video_encoder_import_trim_session"
            )

        self.executable = Path(executable)
        self.runner = runner or subprocess.run

    def convert(self, session):
        result = self.runner(
            [str(self.executable)],
            input=json.dumps(session.to_document()),
            text=True,
            capture_output=True,
            check=False
        )

        if result.returncode != 0:
            raise TrimProjectBridgeError(
                self.error_message(result.stderr)
            )

        return json.loads(result.stdout)

    @staticmethod
    def error_message(stderr):
        try:
            document = json.loads(stderr)
            return document["error"]["message"]
        except (
            json.JSONDecodeError,
            KeyError,
            TypeError
        ):
            message = stderr.strip()

            if message:
                return message

            return "trim project conversion failed"
