"""Conservative language preview; final exported streams remain authoritative."""
from .original_language_review import selection_scope
from .track_options import has_french, has_original, has_subtitles, track_capabilities, preferred_mode


def planned_language(document):
    if document.get("format") == "video_encoder.copy_version":
        return "VOST"
    selection = document.get("track_selection")
    if isinstance(selection, dict):
        try:
            if selection.get("scope") == selection_scope(document):
                return {"french_only": "VF", "original_without_subtitles": "VM",
                        "original_with_subtitles": "VMST"}.get(selection.get("mode"))
        except (KeyError, TypeError):
            pass
        return None
    sources = document.get("sources", [])
    if not isinstance(sources, list) or not sources:
        return None
    inspected = [source.get("inspection") if isinstance(source, dict) else None for source in sources]
    if all(isinstance(item, dict) and has_french(item) and has_original(item) and has_subtitles(item)
           for item in inspected):
        return "VMST"
    for source in sources:
        inspection = source.get("inspection") if isinstance(source, dict) else None
        if not isinstance(inspection, dict):
            return None
        tracks = inspection.get("audio_tracks")
        if not isinstance(tracks, list) or len(tracks) != 1 or not isinstance(tracks[0], dict):
            return None
        track = tracks[0]
        if track.get("visual_impaired"):
            return None
        language = str(track.get("language") or "und").lower()
        if language not in {"fra", "fre", "fr", "und"}:
            return None
    return "VF"


def identification_language(document, inspector=None):
    hint = planned_language(document)
    if hint is not None or isinstance(document.get("track_selection"), dict):
        return hint
    if inspector is None:
        from .media_inspection_client import MediaInspectionClient
        inspector = MediaInspectionClient()
    # Before the first save the identification context contains paths but no timeline or source IDs.
    paths = None if "timeline" in document else [source["path"] for source in document.get("sources", [])]
    capabilities = track_capabilities(document, inspector, source_paths=paths)
    if not capabilities:
        return None
    return {"french_only": "VF", "original_without_subtitles": "VM",
            "original_with_subtitles": "VMST"}.get(preferred_mode(capabilities))
