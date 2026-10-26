from .source_quarantine_client import (
    SourceQuarantineError,
)


class SourceQuarantineController:
    def __init__(
        self,
        client,
        select_source,
        confirm,
        report_success,
        report_failure,
        report_batch=None,
    ):
        self.client = client
        self.select_source = select_source
        self.confirm = confirm
        self.report_success = report_success
        self.report_failure = report_failure
        self.report_batch = report_batch

    def run(self):
        selected = self.select_source()
        if not selected:
            return
        # A single path remains supported for non-UI callers.
        batch = isinstance(selected, (list, tuple))
        paths = list(dict.fromkeys(selected)) if batch else [selected]
        if not self.confirm(paths if batch else selected):
            return

        moved, failed = [], []
        for source_path in paths:
            try:
                self.client.quarantine(source_path)
            except (SourceQuarantineError, OSError) as error:
                failed.append((source_path, str(error)))
            else:
                moved.append(source_path)

        if batch and self.report_batch is not None:
            self.report_batch(moved, failed)
            return
        for source_path in moved:
            self.report_success(source_path)
        for _source_path, message in failed:
            self.report_failure(message)
