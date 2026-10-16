"""Bounded HTTPS reads; credentials are sent only to the GitHub API."""
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .config import SyncError

MAX_BYTES = 5_000_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class GitHub:
    def __init__(self, token: str | None = None):
        self.token = token if token is not None else os.environ.get("GH_TOKEN", os.environ.get("GITHUB_TOKEN", ""))

    def get(self, path: str):
        if not path.startswith("/") or path.startswith("//"):
            raise SyncError("GitHub API paths must be absolute relative paths")
        url = "https://api.github.com" + path
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "dev-handbook/0.1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        opener = build_opener(NoRedirect)
        for attempt in range(3):
            try:
                with opener.open(Request(url, headers=headers), timeout=30) as response:
                    if urlsplit(response.url).hostname != "api.github.com":
                        raise SyncError("Unexpected GitHub API redirect")
                    raw = response.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise SyncError("Source response is too large")
                return json.loads(raw)
            except HTTPError as exc:
                retry = exc.code in (429, 500, 502, 503, 504) or (
                    exc.code == 403 and exc.headers.get("X-RateLimit-Remaining") == "0"
                )
                if not retry or attempt == 2:
                    raise SyncError(f"GitHub HTTP {exc.code}: {path.split('?')[0]}") from None
                try:
                    delay = min(int(exc.headers.get("Retry-After", "0") or 0), 30)
                except ValueError:
                    delay = 0
                time.sleep(max(delay, 2 ** attempt))
            except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
                if attempt == 2:
                    raise SyncError(f"GitHub source unavailable: {type(exc).__name__}") from None
                time.sleep(2 ** attempt)
        raise SyncError("Unreachable request state")
