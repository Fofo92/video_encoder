import json
from pathlib import Path


def empty_detection_report(workspace, source):
    """Recognize a completed full scan with no candidates, including old runs."""
    report = Path(workspace) / "detection" / "pub-candidates.json"
    source = Path(source).resolve()
    try:
        document = json.loads(report.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            return None
        valid = (
            document.get("format") == "video_encoder.6ter_pub_candidates"
            and document.get("version") == 3
            and document.get("complete") is True
            and document.get("ffmpeg_exit_status") == 0
            and document.get("candidate_count") == 0
            and document.get("candidates") == []
            and document.get("requested_start_seconds") is None
            and document.get("requested_duration_seconds") is None
            and document.get("analysed_samples", 0) > 0
            and Path(document["source"]).resolve() == source
            and source.stat().st_mtime_ns <= report.stat().st_mtime_ns
        )
        return report if valid else None
    except (OSError, ValueError, KeyError, TypeError):
        return None
