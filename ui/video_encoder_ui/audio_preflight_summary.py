"""Compact, escaped presentation of the existing audio preflight report."""
from html import escape
from pathlib import Path


STATUS_LABELS = {
    "signal_detected": "signal détecté",
    "inconclusive": "résultat non concluant",
}

MODE_LABELS = {
    "french_only": "VF",
    "french_with_burned_subtitles": "VOST",
    "original_without_subtitles": "VM",
    "original_with_subtitles": "VMST",
}


def audio_preflight_summary(report, output_path):
    output = Path(output_path)
    sources = {}
    for check in report["audio_checks"]:
        sources.setdefault(str(check["source"]), []).append(check)
    subtitles = {str(row["source"]): row for row in report.get("subtitle_selection", [])}
    for source in subtitles:
        sources.setdefault(source, [])
    destination = (
        "<b>Destination</b><br>"
        f"Dossier : {escape(str(output.parent))}<br>"
        f"Nom : {escape(output.stem)}<br>"
        f"Fichiers : projet <b>.json</b> · vidéo <b>{escape(output.suffix)}</b>"
    )
    names = [Path(source).name for source in sources]
    groups = []
    for source, checks in sources.items():
        label = Path(source).name if names.count(Path(source).name) == 1 else source
        tracks = [f"Audio · {track_summary(check)}" for check in checks]
        if report.get("mode") == "french_with_burned_subtitles":
            tracks.append("Sous-titres · incrustés, aucune extraction")
        elif source in subtitles:
            tracks.append(subtitle_summary(subtitles[source]))
        groups.append(f"<b>{escape(label)}</b><br>" + "<br>".join(tracks))
    summary = "<br><br>".join(groups) or "Aucune piste audio à contrôler."
    mode = MODE_LABELS.get(report.get("mode"))
    version = f" — {mode}" if mode else ""
    text = (
        f"{destination}<br><br><b>Sources et pistes{version}</b><br>{summary}<br><br>"
        "Le signal audio est contrôlé, pas la langue. Un résultat non concluant reste à vérifier.<br>"
        "<b>Annuler</b> conserve le montage."
    )
    details = [f"Projet : {output.with_suffix('.json')}", f"Vidéo : {output}"]
    details.extend(f"Source : {source}" for source in sources)
    return text, "\n".join(details)


def subtitle_summary(selection):
    if selection["track_index"] is None:
        return "Sous-titres · aucune piste sélectionnée"
    index = escape(str(selection["track_index"]))
    language = escape(str(selection.get("language") or "non précisée"))
    return f"Sous-titres · piste {index} · {language} — extraction à l’export"


def track_summary(check):
    index = escape(str(check["track_index"]))
    language = escape(str(check.get("language") or "non précisée"))
    status = check["analysis"]["status"]
    label = escape(str(STATUS_LABELS.get(status, status)))
    if status == "inconclusive":
        label = f"<b>{label}</b>"
    return f"Piste {index} · {language} — {label}"
