"""Collect stable releases and commit-pinned stable/preview documentation."""
import base64
import hashlib
import json
import re
from datetime import datetime, timezone
from urllib.parse import quote

from .config import SyncError
from .http import GitHub


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalized(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.replace("\r\n", "\n").splitlines()).strip() + "\n"


def release_record(raw: dict) -> dict:
    if raw.get("draft") or raw.get("prerelease"):
        raise SyncError("Expected a stable release")
    tag = raw["tag_name"]
    if not isinstance(tag, str) or len(tag) > 200 or any(ord(c) < 32 for c in tag):
        raise SyncError("Malformed release tag")
    return {
        "id": raw["id"], "tag": tag, "url": raw["html_url"],
        "published_at": raw["published_at"], "body": raw.get("body") or "",
    }


def collect(config: dict, baseline: dict | None, api: GitHub | None = None) -> dict:
    api = api or GitHub()
    repo = config["repository"]
    latest = release_record(api.get(f"/repos/{repo}/releases/latest"))
    previous_id = baseline["latest"]["id"] if baseline else None
    releases = [latest]
    if previous_id is not None and previous_id != latest["id"]:
        releases = []
        found = False
        for page in range(1, 21):
            batch = api.get(f"/repos/{repo}/releases?per_page=100&page={page}")
            if not isinstance(batch, list):
                raise SyncError("Malformed release listing")
            for raw in batch:
                if raw["id"] == previous_id:
                    found = True
                    break
                if not raw.get("draft") and not raw.get("prerelease"):
                    releases.append(release_record(raw))
            if found:
                break
            if len(batch) < 100:
                break
        if not found:
            raise SyncError("Accepted release missing from history; manual baseline review required")
        if latest["id"] not in {r["id"] for r in releases}:
            raise SyncError("Release history and latest endpoint disagree")
    documents = {}
    refs = {"stable": latest["tag"], "preview": config.get("preview_ref", "main")}
    for channel, ref in refs.items():
        commit = api.get(f"/repos/{repo}/commits/{quote(ref, safe='')}")["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise SyncError("Expected immutable upstream commit")
        for item in config["documents"]:
            raw = api.get(f"/repos/{repo}/contents/{quote(item['path'], safe='/')}?ref={commit}")
            if raw.get("type") != "file" or raw.get("encoding") != "base64":
                raise SyncError(f"Unsupported source file: {item['path']}")
            try:
                content = normalized(base64.b64decode(raw["content"], validate=False).decode("utf-8"))
            except (ValueError, UnicodeError) as exc:
                raise SyncError("Invalid upstream text") from exc
            if len(content.strip()) < 20:
                raise SyncError(f"Unexpected empty source: {item['path']}")
            previous = baseline.get("documents", {}).get(f"{channel}:{item['id']}") if baseline else None
            previous_content = None
            if previous and previous["hash"] != digest(content):
                if "content" in previous:
                    previous_content = previous["content"]
                else:
                    old_path = previous.get("path", item["path"])
                    old = api.get(f"/repos/{repo}/contents/{quote(old_path, safe='/')}?ref={previous['commit']}")
                    if old.get("encoding") != "base64":
                        raise SyncError("Accepted source text cannot be reconstructed")
                    previous_content = normalized(base64.b64decode(old["content"]).decode("utf-8"))
                    if digest(previous_content) != previous["hash"]:
                        raise SyncError("Accepted source checksum mismatch")
            key = f"{channel}:{item['id']}"
            documents[key] = {
                "hash": digest(content), "content": content, "channel": channel,
                "path": item["path"], "previous_content": previous_content,
                "commit": commit, "url": f"https://github.com/{repo}/blob/{commit}/{item['path']}",
                "official_url": item["official_url"], "targets": item["targets"],
            }
    return {
        "schema_version": 1, "tool": config["id"],
        "config_hash": digest(json.dumps(config, sort_keys=True)),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "latest": latest, "releases": releases, "documents": documents,
    }
