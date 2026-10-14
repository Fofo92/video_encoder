import json
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

    def remove(self, job_id):
        result = self.runner(
            [
                str(self.executable),
                "delete-job",
                str(job_id),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise TrimExportQueueError(
                self.error_message(
                    result,
                    fallback="trim export removal failed",
                )
            )

        return result.stdout.strip()

    def manage(self, command, job_id, *options):
        result = self.runner(
            [str(self.executable), command, str(job_id), *map(str, options)],
            text=True, capture_output=True, check=False,
        )
        if result.returncode != 0:
            raise TrimExportQueueError(self.error_message(result, fallback="queue update failed"))
        return result.stdout.strip()

    def defer(self, job_id):
        return self.manage("defer-job", job_id)

    def resume(self, job_id):
        return self.manage("resume-job", job_id)

    def set_output(self, job_id, path):
        return self.manage("set-job-output", job_id, "--output", path)

    def delete_project(self, job_id):
        return self.manage("delete-job", job_id, "--delete-project")

    def list_jobs(self):
        result = self.runner(
            [
                str(self.executable),
                "list",
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        if result.returncode != 0:
            raise TrimExportQueueError(
                self.error_message(
                    result,
                    fallback="trim export queue listing failed",
                )
            )

        try:
            document = json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise TrimExportQueueError(
                "invalid trim export queue response"
            ) from error

        if (
            document.get("format")
            != "video_encoder.job_list"
            or document.get("version") != 1
            or not isinstance(document.get("jobs"), list)
        ):
            raise TrimExportQueueError(
                "unsupported trim export queue response"
            )

        return [
            job
            for job in document["jobs"]
            if job.get("kind") == "trim_export"
        ]

    @staticmethod
    def error_message(
        result,
        fallback="trim export enqueue failed",
    ):
        message = result.stderr.strip()

        if message:
            return message

        message = result.stdout.strip()

        if message:
            return message

        return fallback
