import json
import os
import uuid
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

from .planned_language import planned_language


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VidbProjectLink:
    """Only planned identity is sent; no availability or viewing state is transmitted."""

    def __init__(self, config_path=None, transport=None):
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        self.config_path = Path(config_path or os.environ.get(
            "VIDEO_ENCODER_VIDB_CONFIG", root / "video_encoder" / "vidb.json"))
        self.transport = transport or self.request

    def identify(self, document, destination, refresh=False):
        if not Path(destination).absolute().is_relative_to(Path("/videos")):
            return {"status": "disabled"}
        current = document.get("vidb", {})
        if (isinstance(current, dict) and current.get("status") == "identified"
                and current.get("binding_token") and current.get("project_id") == document.get("project_id")
                and not refresh):
            return current
        if not self.config_path.is_file():
            return {"status": "disabled"}
        try:
            config = self.configuration()
            project = {"project_id": document["project_id"], "project_path": str(Path(destination).absolute()),
                       "output_path": str(Path(destination).absolute().with_suffix(".mkv")),
                       "source_paths": self.source_paths(document)}
            hint = planned_language(document)
            if hint:
                project["language_hint"] = hint
            response = self.transport(config, {"project": project})
            return self.checked_response(config, response, document["project_id"])
        except (OSError, URLError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            if (isinstance(current, dict) and current.get("status") == "identified"
                    and current.get("binding_token") and current.get("project_id") == document.get("project_id")):
                return current
            return {"status": "pending", "reason": "vidb indisponible ; identification à reprendre"}

    def configuration(self):
        if self.config_path.stat().st_size > 4096:
            raise ValueError("configuration trop volumineuse")
        config = json.loads(self.config_path.read_text(encoding="utf-8"))
        parsed = urlparse(config["url"])
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("URL vidb invalide")
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("URL vidb invalide")
        if not isinstance(config.get("token"), str) or len(config["token"]) != 64:
            raise ValueError("secret vidb invalide")
        config["url"] = config["url"].rstrip("/")
        return config

    @staticmethod
    def source_paths(document):
        if document.get("version") == 1:
            return list(dict.fromkeys(item["source"] for item in document.get("timeline", []) if "source" in item))
        return [source["path"] for source in document.get("sources", [])]

    @staticmethod
    def request(config, payload):
        request = Request(config["url"] + "/encoder_projects/identify",
                          data=json.dumps(payload).encode("utf-8"), method="POST",
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + config["token"]})
        with build_opener(NoRedirect()).open(request, timeout=3) as response:
            raw = response.read(65_537)
        if len(raw) > 65_536:
            raise ValueError("réponse vidb trop volumineuse")
        return json.loads(raw)

    @staticmethod
    def checked_response(config, response, project_id):
        if not isinstance(response, dict):
            raise ValueError("réponse vidb invalide")
        status = response.get("status")
        if status == "identified":
            binding = response["binding"]
            if not isinstance(binding, dict):
                raise ValueError("liaison vidb invalide")
            if binding.get("project_id") != project_id or type(binding.get("record_id")) is not int:
                raise ValueError("liaison vidb invalide")
            if binding["record_id"] <= 0 or not isinstance(binding.get("binding_token"), str) or not binding["binding_token"]:
                raise ValueError("liaison vidb invalide")
            result = {key: binding[key] for key in ("project_id", "record_id", "binding_token")}
            result.update(status="identified", record_title=response.get("record_title", ""))
            if isinstance(response.get("metadata"), dict):
                result["metadata"] = response["metadata"]
            review_url = response.get("review_url")
            if review_url:
                if urlparse(review_url).netloc != urlparse(config["url"]).netloc or urlparse(review_url).scheme != "https":
                    raise ValueError("lien de complément hors de vidb")
                result["review_url"] = review_url
            return result
        if status not in {"needs_review", "unmatched"}:
            raise ValueError("réponse vidb invalide")
        review_url = response.get("review_url", "")
        if urlparse(review_url).netloc != urlparse(config["url"]).netloc or urlparse(review_url).scheme != "https":
            raise ValueError("lien de validation hors de vidb")
        return {"status": status, "review_url": review_url, "reason": response.get("reason", "")}

    @staticmethod
    def project_id(session):
        existing = getattr(session, "project_id", None)
        try:
            parsed = uuid.UUID(str(existing))
            if parsed.version == 4:
                return str(parsed)
        except (ValueError, TypeError, AttributeError):
            pass
        return str(uuid.uuid4())
