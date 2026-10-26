import re
import unicodedata
from pathlib import Path

from PySide6 import QtWidgets

from .vidb_project_link import VidbProjectLink
from .vidb_project_context import project_identification_context
from .episode_destination import suggested_episode_output
from .vidb_export_review import await_vidb_identification
from .vidb_modal_browser import open_vidb_modal


def suggested_film_output(metadata, suggested, film_root=Path("/videos/Films")):
    from .title_convention import title_with_original

    title = title_with_original(metadata)
    basename = re.sub(r"[/\\\x00-\x1f]", "_", title).strip(" .")
    basename = basename.encode("utf-8")[:220].decode("utf-8", errors="ignore")
    if not basename:
        return Path(suggested)
    documentary = any(genre_key(value) == "documentaire" for value in metadata.get("genres", [])
                      if isinstance(value, str))
    if documentary:
        documentary_root = Path("/videos/Documentaires")
        directory = Path(suggested).parent if Path(suggested).is_relative_to(documentary_root) else documentary_root
    else:
        directory = genre_directory(metadata.get("genres", []), film_root) or Path(suggested).parent
    return directory / f"{basename}.mkv"


def genre_key(value):
    plain = unicodedata.normalize("NFKD", value).encode("ascii", errors="ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", plain.casefold())


def genre_directory(genres, film_root):
    if (not isinstance(genres, list) or not 1 <= len(genres) <= 2
            or any(not isinstance(genre, str) or genre in {".", ".."}
                   or "/" in genre or "\\" in genre or "," in genre for genre in genres)):
        return None
    expected = {genre_key(genre) for genre in genres}
    if "" in expected or len(expected) != len(genres):
        return None
    try:
        matches = [folder for folder in Path(film_root).iterdir()
                   if folder.is_dir() and {genre_key(part.strip()) for part in folder.name.split(",")} == expected]
    except OSError:
        return None
    return matches[0] if len(matches) == 1 else None


def documentary_fallback(suggested, source=None):
    path = Path(suggested)
    # Preserve an already chosen destination, including documentary subfolders.
    if path.parent != Path("/videos"):
        return path
    if source is not None and Path(source).is_relative_to(Path("/videos/Documentaires")):
        return Path("/videos/Documentaires") / path.name
    return path


def prepare_catalogue_destination(parent, session, source, suggested, writer, continue_export=False):
    suggested = documentary_fallback(suggested, source)
    link = getattr(writer, "vidb_link", None)
    if not isinstance(link, VidbProjectLink) or session is None:
        return Path(suggested)
    if not any(Path(source).absolute().is_relative_to(Path(root)) for root in ("/commun", "/videos")):
        return Path(suggested)
    document, provisional = project_identification_context(session, source, suggested)
    result = link.identify(document, provisional, refresh=True)
    writer.vidb_result = result
    if result.get("status") == "disabled":
        return Path(suggested)
    if result.get("status") != "identified":
        if not continue_export:
            return review_before_destination(parent, result, suggested)
        result = await_vidb_identification(
            parent, result, lambda: link.identify(document, provisional, refresh=True))
        if result is None:
            return None
        writer.vidb_result = result
        if result.get("status") != "identified":
            return Path(suggested)
    session.vidb = {key: value for key, value in result.items() if key != "metadata"}
    metadata = result.get("metadata", {})
    complete = all(metadata.get(field) for field in ("year", "abstract", "genres", "countries"))
    if metadata.get("record_kind") == "episode":
        if continue_export and complete and metadata.get("language_version") not in (None, "", "IND"):
            return suggested_episode_output(metadata, suggested)
        return confirm_episode_destination(
            parent, metadata, suggested, result.get("review_url"),
            refresh=(lambda: link.identify(document, provisional, refresh=True)) if continue_export else None)
    if metadata.get("record_kind") != "standalone_video":
        return Path(suggested)
    if continue_export and complete:
        return suggested_film_output(metadata, suggested)
    return confirm_destination(parent, metadata, suggested)


def review_before_destination(parent, result, suggested):
    dialog = QtWidgets.QMessageBox(parent)
    dialog.setWindowTitle("Identifier l’œuvre avant de choisir sa destination")
    dialog.setText("La fiche vidb permettra de proposer le titre, l’année et le classement de l’œuvre.")
    dialog.setInformativeText("Tu peux rechercher l’œuvre et créer sa fiche dans vidb, puis reprendre "
                              "l’enregistrement de ce montage. Les coupures restent dans la fenêtre ouverte.")
    open_button = None
    if result.get("review_url"):
        open_button = dialog.addButton("Identifier ou créer la fiche dans vidb", QtWidgets.QMessageBox.ButtonRole.ActionRole)
        dialog.setDefaultButton(open_button)
    manual = dialog.addButton("Choisir la destination maintenant", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    dialog.addButton("Revenir au montage", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    dialog.exec()
    if open_button is not None and dialog.clickedButton() is open_button:
        open_vidb_modal(parent, result["review_url"])
        return None
    return Path(suggested) if dialog.clickedButton() is manual else None


def confirm_destination(parent, metadata, suggested):
    proposed = suggested_film_output(metadata, suggested)
    dialog = QtWidgets.QMessageBox(parent)
    dialog.setWindowTitle("Film identifié dans vidb")
    dialog.setText(f"{metadata.get('french_title') or metadata.get('original_title')}\n"
                   f"Année : {metadata.get('year') or 'à compléter'}\n"
                   f"Genres : {', '.join(metadata.get('genres', [])) or 'à compléter'}\n"
                   f"Pays : {', '.join(metadata.get('countries', [])) or 'à compléter'}")
    explanation = f"Destination proposée :\n{proposed}\n\nTu pourras l’ajuster dans la fenêtre suivante."
    if (not proposed.is_relative_to(Path("/videos/Documentaires"))
            and genre_directory(metadata.get("genres", []), Path("/videos/Films")) is None):
        explanation += "\nAucun dossier unique correspondant à tous les genres : vérifie le répertoire choisi."
    dialog.setInformativeText(explanation)
    dialog.setDetailedText(metadata.get("abstract", ""))
    use = dialog.addButton("Utiliser cette proposition", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    dialog.setDefaultButton(use)
    manual = dialog.addButton("Choisir moi-même", QtWidgets.QMessageBox.ButtonRole.ActionRole)
    dialog.addButton("Revenir au montage", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    dialog.exec()
    if dialog.clickedButton() is use:
        return proposed
    return proposed if dialog.clickedButton() is manual else None


def confirm_episode_destination(parent, metadata, suggested, review_url=None, refresh=None):
    proposed = suggested_episode_output(metadata, suggested)
    dialog = QtWidgets.QMessageBox(parent)
    dialog.setWindowTitle("Épisode identifié dans vidb")
    dialog.setText(f"Destination proposée :\n{proposed}")
    missing = [label for field, label in (("year", "année"), ("abstract", "résumé"),
                                         ("genres", "genres"), ("countries", "pays")) if not metadata.get(field)]
    if metadata.get("language_version") in (None, "", "IND"):
        missing.append("version linguistique")
    explanation = "Vérifie le dossier de la série et de la saison dans la fenêtre suivante."
    if missing:
        explanation += "\nÀ compléter dans vidb : " + ", ".join(missing) + "."
    dialog.setInformativeText(explanation)
    complete = None
    if review_url:
        complete = dialog.addButton("Compléter la fiche dans vidb", QtWidgets.QMessageBox.ButtonRole.ActionRole)
    use = dialog.addButton("Utiliser cette proposition", QtWidgets.QMessageBox.ButtonRole.AcceptRole)
    dialog.setDefaultButton(use)
    manual = dialog.addButton("Choisir moi-même", QtWidgets.QMessageBox.ButtonRole.ActionRole)
    dialog.addButton("Revenir au montage", QtWidgets.QMessageBox.ButtonRole.RejectRole)
    dialog.exec()
    if complete is not None and dialog.clickedButton() is complete:
        if refresh is not None:
            updated = await_vidb_identification(
                parent, {"status": "identified", "metadata": metadata, "review_url": review_url}, refresh)
            if updated is None:
                return None
            return suggested_episode_output(updated.get("metadata", metadata), suggested)
        open_vidb_modal(parent, review_url)
        return None
    if dialog.clickedButton() is use:
        return proposed
    return Path(suggested) if dialog.clickedButton() is manual else None
