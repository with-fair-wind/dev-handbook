"""Validate metadata, local links, generated blocks and changed-file boundaries."""
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

from .config import SyncError, inside

REQUIRED = {"title", "sources_checked_at", "content_reviewed_at", "tested_versions", "tested_environment", "pending_changes"}
MARKER = re.compile(r"<!-- AUTO:(BEGIN|END) ([a-z0-9-]+) -->")


def metadata(text: str) -> dict:
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not match:
        raise SyncError("Document needs YAML front matter")
    data = yaml.safe_load(match.group(1))
    if not isinstance(data, dict) or not REQUIRED <= data.keys():
        raise SyncError("Missing document metadata")
    if not isinstance(data["tested_versions"], list):
        raise SyncError("tested_versions must be an explicit list")
    return data


def check_text(text: str):
    metadata(text)
    stack = []
    seen = set()
    for kind, name in MARKER.findall(text):
        if kind == "BEGIN":
            if name in seen or stack:
                raise SyncError("Duplicate or nested AUTO block")
            seen.add(name)
            stack.append(name)
        elif not stack or stack.pop() != name:
            raise SyncError("Unmatched AUTO block")
    if stack:
        raise SyncError("Unclosed AUTO block")
    if re.search(r"(?m)^(<{7}|={7}|>{7})(?: |$)", text):
        raise SyncError("Unresolved merge conflict")
    if re.search(r"(?:gh[pousr]_[A-Za-z0-9]{25,}|sk-[A-Za-z0-9]{30,}|-----BEGIN .*PRIVATE KEY-----)", text):
        raise SyncError("Possible credential in document")


def outside_blocks(text: str) -> str:
    text = re.sub(r"(?m)^sources_checked_at:.*$", "sources_checked_at: <managed>", text)
    return re.sub(r"<!-- AUTO:BEGIN ([a-z0-9-]+) -->.*?<!-- AUTO:END \1 -->", "", text, flags=re.S)


def validate_changes(root: Path, config: dict, changes: dict[str, str]):
    permitted = {config["release_summary"], config["history"], "state/sources.lock.json"}
    for item in config["documents"]:
        permitted.update(item["targets"])
    for relative, new in changes.items():
        if relative not in permitted:
            raise SyncError(f"Unauthorized output path: {relative}")
        path = inside(root, relative)
        if relative.endswith(".md"):
            old = path.read_text(encoding="utf-8")
            check_text(new)
            if outside_blocks(old) != outside_blocks(new):
                raise SyncError(f"Personal content changed: {relative}")
            if MARKER.findall(old) != MARKER.findall(new):
                raise SyncError("Generated blocks cannot be added, removed or reordered")


def check_repository(root: Path) -> int:
    count = 0
    for path in sorted((root / "docs").rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            check_text(text)
            # Ignore fenced code and raw HTML diffs before validating Markdown links.
            plain = re.sub(r"```.*?```|<pre>.*?</pre>", "", text, flags=re.S)
            for target in re.findall(r"!?(?:\[[^\]]*\])\(([^\s)]+)(?:\s+[^)]*)?\)", plain):
                split = urlsplit(target)
                if split.scheme or target.startswith(("#", "//")):
                    continue
                if not split.path:
                    continue
                resolved = (path.parent / unquote(split.path)).resolve()
                if not resolved.is_relative_to((root / "docs").resolve()) or not resolved.exists():
                    raise SyncError(f"Broken local link: {target}")
        except SyncError as exc:
            raise SyncError(f"{path.relative_to(root)}: {exc}") from exc
        count += 1
    if not count:
        raise SyncError("No documents found")
    return count


def validate_candidate(root: Path, changes: dict[str, str]):
    """Build the candidate in an isolated directory before any remote write."""
    import shutil
    import subprocess
    import sys
    import tempfile

    with tempfile.TemporaryDirectory(prefix="docsync-check-") as directory:
        temp = Path(directory)
        shutil.copytree(root / "docs", temp / "docs")
        shutil.copy2(root / "mkdocs.yml", temp / "mkdocs.yml")
        for path, text in changes.items():
            if path.startswith("docs/"):
                target = inside(temp, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
        check_repository(temp)
        result = subprocess.run(
            [sys.executable, "-m", "mkdocs", "build", "--strict", "--config-file",
             str(temp / "mkdocs.yml"), "--site-dir", str(temp / "site")],
            text=True, encoding="utf-8", capture_output=True
        )
        if result.returncode:
            raise SyncError("Candidate strict MkDocs build failed: " + result.stderr[-1500:])
