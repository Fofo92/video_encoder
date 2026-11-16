"""A browser ticket selects a record; the existing bridge authenticates the client."""
import json
import uuid
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, build_opener


class LaunchError(ValueError):
    pass


def checked_ticket(ticket):
    if not isinstance(ticket, str) or not ticket or len(ticket) > 6000:
        raise LaunchError("Demande de montage invalide ; reprends la préparation depuis vidb.")
    return ticket


def parse_launch_url(url, origin):
    if not isinstance(url, str) or len(url) > 8192 or any(ord(char) < 32 for char in url):
        raise LaunchError("Lien de préparation invalide.")
    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=True, strict_parsing=True)
    if (parts.scheme != "vidb-encoder" or parts.netloc != "prepare" or parts.path not in ("", "/")
            or parts.fragment or set(query) != {"ticket", "origin"}
            or any(len(values) != 1 for values in query.values())
            or query["origin"][0].rstrip("/") != origin.rstrip("/")):
        raise LaunchError("Ce lien ne correspond pas à la passerelle vidb configurée sur ce poste.")
    return checked_ticket(query["ticket"][0])


def request_launch(config, ticket, project=None):
    from .vidb_project_link import NoRedirect

    payload = {"launch_token": ticket}
    if project is not None:
        payload["project"] = project
    request = Request(config["url"] + "/encoder_projects/launch_binding",
                      data=json.dumps(payload).encode("utf-8"), method="POST",
                      headers={"Content-Type": "application/json", "Authorization": "Bearer " + config["token"]})
    try:
        with build_opener(NoRedirect()).open(request, timeout=3) as response:
            raw = response.read(65_537)
    except HTTPError as error:
        raise refused_launch(error) from error
    if len(raw) > 65_536:
        raise LaunchError("Réponse de préparation trop volumineuse.")
    result = json.loads(raw)
    if not isinstance(result, dict) or result.get("error"):
        raise LaunchError("La demande vidb a été refusée ; recharge la fiche et réessaie.")
    return result


def refused_launch(error):
    message = "La demande vidb a été refusée ; recharge la fiche et réessaie."
    try:
        result = json.loads(error.read(65_537))
        detail = result.get("error") if isinstance(result, dict) else None
        if isinstance(detail, str) and 0 < len(detail) <= 500:
            message = detail
    except (OSError, ValueError):
        pass
    return LaunchError(message)


def checked_context(data):
    try:
        project_id = data["project_id"]
        if str(uuid.UUID(project_id, version=4)) != project_id or uuid.UUID(project_id).version != 4:
            raise ValueError("invalid project")
        if type(data["record_id"]) is not int or data["record_id"] <= 0:
            raise ValueError("invalid record")
        if not isinstance(data["record_title"], str) or len(data["record_title"]) > 4000:
            raise ValueError("invalid title")
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise LaunchError("Réponse de préparation vidb invalide.") from error
    return data
