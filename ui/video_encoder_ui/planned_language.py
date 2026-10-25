"""Conservative language preview; final exported streams remain authoritative."""


def planned_language(document):
    sources = document.get("sources", [])
    if not isinstance(sources, list) or not sources:
        return None
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
