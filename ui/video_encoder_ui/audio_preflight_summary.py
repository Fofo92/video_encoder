"""Compact, escaped presentation of the existing audio preflight report."""
from html import escape
from pathlib import Path


STATUS_LABELS = {
    "signal_detected": "signal détecté",
    "inconclusive": "résultat non concluant",
}


def audio_preflight_summary(report, output_path):
    output = Path(output_path)
    sources = {}
    for check in report["audio_checks"]:
        sources.setdefault(str(check["source"]), []).append(check)
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
        tracks = "<br>".join(track_summary(check) for check in checks)
        groups.append(f"<b>{escape(label)}</b><br>{tracks}")
    summary = "<br><br>".join(groups) or "Aucune piste audio à contrôler."
    text = (
        f"{destination}<br><br><b>Sources et pistes</b><br>{summary}<br><br>"
        "Le signal audio est contrôlé, pas la langue. Un résultat non concluant reste à vérifier.<br>"
        "<b>Annuler</b> conserve le montage."
    )
    details = [f"Projet : {output.with_suffix('.json')}", f"Vidéo : {output}"]
    details.extend(f"Source : {source}" for source in sources)
    return text, "\n".join(details)


def track_summary(check):
    index = escape(str(check["track_index"]))
    language = escape(str(check.get("language") or "non précisée"))
    status = check["analysis"]["status"]
    label = escape(str(STATUS_LABELS.get(status, status)))
    if status == "inconclusive":
        label = f"<b>{label}</b>"
    return f"Piste {index} · {language} — {label}"
