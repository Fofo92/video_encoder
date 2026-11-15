"""Track-profile availability for the sources actually used by a montage."""

FRENCH = {"fra", "fre"}
MODE_LABELS = {
    "french_only": "VF — français et sous-titres forcés uniquement",
    "original_without_subtitles": "VM — français et VO, sans sous-titres complets",
    "original_with_subtitles": "VMST — français, VO et sous-titres français",
}


def used_source_paths(document):
    timeline = [item for item in document.get("timeline", []) if item.get("type", "segment") == "segment"]
    if document.get("version") == 1:
        return list(dict.fromkeys(item["source"] for item in timeline))
    sources = {source["id"]: source["path"] for source in document.get("sources", [])}
    return list(dict.fromkeys(sources[item["source_id"]] for item in timeline))


def track_capabilities(document, inspector=None, *, source_paths=None):
    paths = used_source_paths(document) if source_paths is None else list(dict.fromkeys(source_paths))
    if not paths:
        return None
    cached = {source.get("path"): source.get("inspection") for source in document.get("sources", [])}
    inspections = {}
    for path in paths:
        details = inspector.inspect(path).get("inspection") if inspector is not None else cached.get(path)
        if not isinstance(details, dict):
            return None
        inspections[path] = details
    french = all(has_french(details) for details in inspections.values())
    original = all(has_original(details) for details in inspections.values())
    subtitles = all(has_subtitles(details) for details in inspections.values())
    return {"french_only": french, "original_without_subtitles": french and original,
            "original_with_subtitles": french and original and subtitles, "inspections": inspections}


def has_french(details):
    return any(track.get("language") in FRENCH and not track.get("visual_impaired")
               for track in details.get("audio_tracks", []))


def has_original(details):
    return any(track.get("language") == "qaa" and not track.get("visual_impaired")
               for track in details.get("audio_tracks", []))


def has_subtitles(details):
    return any(track.get("language") in FRENCH and not track.get("hearing_impaired") and not track.get("forced")
               for track in details.get("subtitle_tracks", []))


def preferred_mode(capabilities):
    for mode in ("original_with_subtitles", "original_without_subtitles", "french_only"):
        if capabilities.get(mode):
            return mode
    return None


def choose_track_mode(parent, capabilities, current=None):
    from PySide6 import QtWidgets

    box = QtWidgets.QMessageBox(parent)
    box.setWindowTitle("Pistes du nouvel encodage")
    box.setText("Choisis les pistes à conserver dans le nouvel encodage.\n"
                "VMST est proposé lorsque toutes les sources utilisées le permettent.")
    previous = MODE_LABELS.get(current, "aucun choix enregistré")
    box.setInformativeText("VF : français et sous-titres forcés uniquement.\n"
                           "VM : français et VO, sans sous-titres complets.\n"
                           "VMST : français, VO et sous-titres français.\n\n"
                           f"Choix précédent : {previous}.\n"
                           "L’ancien encodage et son projet ne seront pas remplacés.")
    cancel = box.addButton("Annuler", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    buttons = {}
    for mode, label in MODE_LABELS.items():
        button = box.addButton(label.split(" — ", 1)[0], QtWidgets.QMessageBox.ButtonRole.ActionRole)
        button.setEnabled(bool(capabilities.get(mode)))
        button.setToolTip(label if capabilities.get(mode) else "Des pistes requises manquent sur au moins une source utilisée.")
        buttons[mode] = button
    preferred = preferred_mode(capabilities)
    box.setDefaultButton(buttons[preferred] if preferred else cancel)
    box.setEscapeButton(cancel)
    box.exec()
    return next((mode for mode, button in buttons.items()
                 if button.isEnabled() and box.clickedButton() is button), None)
