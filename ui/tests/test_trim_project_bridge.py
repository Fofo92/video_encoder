import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from video_encoder_ui.trim_project_bridge import (
    TrimProjectBridge,
    TrimProjectBridgeError,
)


class TrimProjectBridgeTest(unittest.TestCase):
    def test_converts_the_session_with_the_ruby_bridge(self):
        session = Mock()
        session.to_document.return_value = {
            "format": "video_encoder.trim_session",
            "version": 1,
            "sources": [],
            "timeline": []
        }

        runner = Mock(
            return_value=SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "format": "video_encoder.trim_project",
                        "version": 1,
                        "timeline": []
                    }
                ),
                stderr=""
            )
        )

        bridge = TrimProjectBridge(
            executable="/project/bin/import",
            runner=runner
        )

        project = bridge.convert(session)

        self.assertEqual(
            project["format"],
            "video_encoder.trim_project"
        )

        arguments, options = runner.call_args

        self.assertEqual(
            arguments,
            (["/project/bin/import"],)
        )
        self.assertEqual(
            json.loads(options["input"]),
            session.to_document.return_value
        )
        self.assertTrue(options["text"])
        self.assertTrue(options["capture_output"])
        self.assertFalse(options["check"])

    def test_reports_the_error_returned_by_ruby(self):
        session = Mock()
        session.to_document.return_value = {
            "format": "video_encoder.trim_session",
            "version": 1,
            "sources": [],
            "timeline": []
        }
        runner = Mock(
            return_value=SimpleNamespace(
                returncode=1,
                stdout="",
                stderr=json.dumps(
                    {
                        "error": {
                            "type": "ArgumentError",
                            "message": "unknown source identifier: C"
                        }
                    }
                )
            )
        )

        bridge = TrimProjectBridge(
            executable=Path("/project/bin/import"),
            runner=runner
        )

        with self.assertRaisesRegex(
            TrimProjectBridgeError,
            "unknown source identifier: C"
        ):
            bridge.convert(session)


if __name__ == "__main__":
    unittest.main()
