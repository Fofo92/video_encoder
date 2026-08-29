import re


class MltProgressParser:
    PROGRESS_PATTERN = re.compile(
        r"percentage:\s*(\d+)"
    )

    def __init__(self):
        self.buffer = ""
        self.last_percentage = None

    def feed(self, output):
        self.buffer += output

        lines = re.split(
            r"[\r\n]",
            self.buffer
        )

        if self.buffer.endswith(("\r", "\n")):
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
        percentages = []
        diagnostics = []

        for line in lines:
            if not line:
                continue

            match = self.PROGRESS_PATTERN.search(line)

            if match is None:
                diagnostics.append(line)
                continue

            percentage = max(
                0,
                min(int(match.group(1)), 100)
            )

            if percentage == self.last_percentage:
                continue

            self.last_percentage = percentage
            percentages.append(percentage)

        return percentages, diagnostics
