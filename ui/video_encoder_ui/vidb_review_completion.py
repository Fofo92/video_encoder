import re
from urllib.parse import parse_qs, urlsplit


def completed_record(url, review_url):
    """A successful vidb form redirects to this record; recognition alone is insufficient."""
    try:
        current, expected = urlsplit(url), urlsplit(review_url)
        if (current.scheme != "https" or expected.scheme != "https"
                or current.username or current.password
                or current.hostname != expected.hostname
                or (current.port or 443) != (expected.port or 443)):
            return None
        if parse_qs(current.query).get("encoder_prepared") != ["1"]:
            return None
        match = re.fullmatch(r"/records/([1-9][0-9]*)", current.path)
        return int(match[1]) if match else None
    except ValueError:
        return None


def watch_completion(browser, review_url, callback):
    if not hasattr(browser, "urlChanged"):
        return

    def changed(url):
        record_id = completed_record(url.toString(), review_url)
        if record_id is not None:
            callback(record_id)

    browser.urlChanged.connect(changed)
