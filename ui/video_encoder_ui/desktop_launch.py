"""Open a source locally, retaining the user's record choice until identification."""
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit

from .vidb_launch_client import (
    LaunchError, checked_context, checked_desktop_action, parse_desktop_url, parse_launch_url, request_launch,
)


def dispatch_from_vidb(url, *, link, editor_controller, select_source, actions, report, transport=request_launch):
    try:
        if urlsplit(url).netloc == "prepare":
            return open_from_vidb(url, link=link, editor_controller=editor_controller,
                                  select_source=select_source, report=report, transport=transport)
        config = link.configuration()
        ticket = parse_desktop_url(url, config["url"])
        action = checked_desktop_action(transport(config, ticket, desktop=True))
        callback = actions.get(action)
        if not callable(callback):
            raise LaunchError("Cette commande video_encoder n’est pas disponible.")
        callback()
        return True
    except (OSError, URLError, ValueError, KeyError, TypeError, RuntimeError) as error:
        report(str(error))
        return False


def open_from_vidb(url, *, link, editor_controller, select_source, report, transport=request_launch):
    try:
        config = link.configuration()
        ticket = parse_launch_url(url, config["url"])
        context = checked_context(transport(config, ticket))
        current = editor_controller.editor_window
        if current is not None and getattr(current.trim_session, "project_id", None) == context["project_id"]:
            current.show()
            current.raise_()
            current.activateWindow()
            return True
        selected = select_source(context["record_title"])
        if not selected:
            return False
        source = Path(selected).expanduser()
        if not source.is_absolute() or not source.is_file() or source.suffix.lower() == ".json":
            raise ValueError("Choisis un fichier source vidéo existant, pas un projet JSON.")
        previous = editor_controller.editor_window
        editor_controller.open(source)
        editor = editor_controller.editor_window
        if editor is None or editor is previous:
            return False
        session = editor.trim_session
        session.project_id = context["project_id"]
        session.vidb_launch = ticket
        editor.set_project_modified(True)
        editor.statusBar().showMessage(f"Montage pour la fiche {context['record_id']} · {context['record_title']}", 15_000)
        return True
    except (OSError, URLError, ValueError, KeyError, TypeError) as error:
        report(str(error))
        return False
