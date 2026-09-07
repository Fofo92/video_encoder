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
    ):
        self.client = client
        self.select_source = select_source
        self.confirm = confirm
        self.report_success = report_success
        self.report_failure = report_failure

    def run(self):
        source_path = self.select_source()

        if source_path is None:
            return

        if not self.confirm(source_path):
            return

        try:
            self.client.quarantine(source_path)
        except SourceQuarantineError as e:
            self.report_failure(str(e))
            return

        self.report_success(source_path)
