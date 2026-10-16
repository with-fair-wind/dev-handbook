"""Load trusted repository configuration and enforce write boundaries."""
from pathlib import Path, PurePosixPath
import re

import yaml


class SyncError(RuntimeError):
    """An incomplete or unsafe update; never advance the baseline."""


def inside(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or "\\" in relative:
        raise SyncError("Paths must be repository-relative POSIX strings")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts or ":" in relative:
        raise SyncError(f"Unsafe path: {relative}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise SyncError(f"Path escapes repository: {relative}")
    return target


def load_config(root: Path, tool: str) -> dict:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", tool):
        raise SyncError("Invalid tool ID")
    data = yaml.safe_load(inside(root, f"sources/{tool}.yml").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("id") != tool:
        raise SyncError("Unsupported source configuration")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", data["repository"]):
        raise SyncError("Invalid upstream repository")
    if not data.get("documents"):
        raise SyncError("At least one upstream document is required")
    ids = set()
    for item in data["documents"]:
        if not re.fullmatch(r"[a-z0-9-]+", item["id"]) or item["id"] in ids:
            raise SyncError("Duplicate or invalid document ID")
        ids.add(item["id"])
        inside(root, item["path"])
        if not item["official_url"].startswith("https://"):
            raise SyncError("Official URLs must use HTTPS")
        for path in item["targets"]:
            check_doc_path(root, tool, path)
    for key in ("release_summary", "history"):
        check_doc_path(root, tool, data[key])
    return data


def check_doc_path(root: Path, tool: str, relative: str) -> Path:
    path = inside(root, relative)
    if not relative.startswith(f"docs/tools/{tool}/") or not relative.endswith(".md"):
        raise SyncError(f"Not an authorized tool document: {relative}")
    return path


def allowed_paths(config: dict) -> set[str]:
    return {config["release_summary"], config["history"], "state/sources.lock.json"}
