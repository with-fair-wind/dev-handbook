"""docsync check / sync / links: local preview by default, publication explicit."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from . import ai
from .collect import collect
from .compare import compare
from .config import SyncError, inside, load_config
from .github import Publisher
from .render import plan_files, report
from .validate import check_repository, validate_candidate, validate_changes


def load_state(root):
    data = json.loads(inside(root, "state/sources.lock.json").read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("tools"), dict):
        raise SyncError("Unsupported accepted state")
    return data


def update(root, tool, fixture=None, apply=False, publish=False, repository=None, use_ai=False):
    config = load_config(root, tool)
    state = load_state(root)
    baseline = state["tools"].get(tool)
    # Fixture data is only for offline preview/tests; never a publishing input.
    if publish and fixture:
        raise SyncError("Fixture input cannot be published")
    candidate = json.loads(Path(fixture).read_text(encoding="utf-8")) if fixture else collect(config, baseline)
    if candidate.get("tool") != tool or candidate.get("schema_version") != 1:
        raise SyncError("Snapshot tool/schema mismatch")
    expected = {f"{channel}:{d['id']}" for channel in ("stable", "preview") for d in config["documents"]}
    if set(candidate["documents"]) != expected:
        raise SyncError("Incomplete source snapshot")
    delta = compare(baseline, candidate)
    output = root / ".docsync" / tool
    output.mkdir(parents=True, exist_ok=True)
    (output / "candidate.json").write_text(json.dumps(candidate, ensure_ascii=False, indent=2), encoding="utf-8")
    publisher = Publisher(root, repository, tool) if publish and repository else None
    if publish and not publisher:
        raise SyncError("--publish requires --repository or GITHUB_REPOSITORY")
    if not delta["changed"]:
        text = "所有登记来源已成功检查；没有内容变化，未改动文档。\n"
        (output / "report.md").write_text(text, encoding="utf-8")
        if publisher:
            publisher.recovered()
        return {"changed": False, "report": str(output / "report.md")}
    # Include local main content + baseline in the dedup key so a new base is re-reviewed.
    local = {
        p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
        for p in (root / "docs" / "tools" / tool).glob("*.md")
    }
    key = hashlib.sha256(json.dumps({
        "candidate": delta["fingerprint"], "state": state, "config": config, "docs": local,
        "generator": {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted(Path(__file__).parent.glob("*.py"))},
    }, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    if publisher:
        status = publisher.inspect(key)
        if status["skip"]:
            (output / "report.md").write_text(status["reason"] + "\n" + status["url"] + "\n", encoding="utf-8")
            publisher.recovered()
            return {"changed": False, **status}
    changes = plan_files(root, config, state, candidate, delta)
    ai_note = "AI 未启用；使用规则生成报告。"
    if use_ai:
        changes, ai_note = ai.generate(root, config, candidate, delta, changes)
    validate_changes(root, config, changes)
    validate_candidate(root, changes)
    body = report(config, baseline, candidate, delta) + "\n" + ai_note + "\n\n候选文档元数据、内部链接、生成边界及 MkDocs 严格构建：已通过。\n"
    (output / "report.md").write_text(body, encoding="utf-8")
    (output / "changes.json").write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8")
    # Publishing uses the API and leaves the main checkout untouched.
    if publisher:
        url = publisher.publish(changes, f"docs({tool}): 核对官方来源 {candidate['latest']['tag']}", body, key)
        publisher.recovered()
        return {"changed": True, "pull_request": url, "report": str(output / "report.md")}
    if apply:
        for path, content in changes.items():
            inside(root, path).write_text(content, encoding="utf-8")
    return {"changed": True, "applied": apply, "report": str(output / "report.md"), "files": list(changes)}


def external_links(root):
    import re

    urls = set()
    for file in (root / "docs").rglob("*.md"):
        urls.update(re.findall(r"\]\((https://[^\s)]+)\)", file.read_text(encoding="utf-8")))
    failed, transient = [], []
    for url in sorted(urls):
        if urlsplit(url).username or urlsplit(url).password:
            failed.append(url)
            continue
        try:
            with urlopen(Request(url, headers={"User-Agent": "dev-handbook-link-check"}), timeout=20) as response:
                if response.status >= 400:
                    transient.append(url)
        except HTTPError as exc:
            (failed if exc.code in (404, 410) else transient).append(url)
        except (URLError, TimeoutError, OSError):
            transient.append(url)
    return {"checked": len(urls), "broken": failed, "inconclusive": transient}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check")
    sub.add_parser("links")
    sync = sub.add_parser("sync")
    sync.add_argument("--tool", default="oh-my-posh")
    sync.add_argument("--fixture", type=Path)
    sync.add_argument("--apply", action="store_true")
    sync.add_argument("--publish", action="store_true")
    sync.add_argument("--ai", action="store_true")
    sync.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY"))
    sync.add_argument("--notify-failure", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == "check":
            load_state(root)
            for path in (root / "sources").glob("*.yml"):
                load_config(root, path.stem)
            result = {"documents_checked": check_repository(root)}
        elif args.command == "links":
            result = external_links(root)
        else:
            result = update(root, args.tool, args.fixture, args.apply, args.publish, args.repository, args.ai)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        summary = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary:
            with open(summary, "a", encoding="utf-8") as stream:
                stream.write("### 文档自动更新\n\n" + json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        return 1 if result.get("broken") else 0
    except Exception as exc:
        message = str(exc) if isinstance(exc, SyncError) else type(exc).__name__
        print(f"更新未完成：{message}", file=sys.stderr)
        if args.command == "sync" and args.notify_failure and args.repository:
            try:
                Publisher(root, args.repository, args.tool).failure(message)
            except SyncError:
                print("失败通知不可用，请查看 Actions 记录。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
