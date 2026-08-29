import json


class ExportEventParser:
    PREFIX = "VIDEO_ENCODER_EXPORT_EVENT "

    def __init__(self):
        self.buffer = ""

    def feed(self, output):
        self.buffer += output
        lines = self.buffer.split("\n")

        if self.buffer.endswith("\n"):
            self.buffer = ""
        else:
            self.buffer = lines.pop()

        return self.parse_lines(lines)

    def finish(self):
        if not self.buffer:
            return [], []

        line = self.buffer
        self.buffer = ""

        return self.parse_lines([line])

    def parse_lines(self, lines):
        events = []
        diagnostics = []

        for line in lines:
            if not line:
                continue

            if not line.startswith(self.PREFIX):
                diagnostics.append(line)
                continue

            payload = line.removeprefix(
                self.PREFIX
            )

            try:
                events.append(
                    json.loads(payload)
                )
            except json.JSONDecodeError:
                diagnostics.append(line)

        return events, diagnostics
