"""Render reviewable metadata and reports without rewriting personal instructions."""
import difflib
import html
import json
import re
from datetime import datetime, timezone

from .config import SyncError, inside


def replace_block(text: str, name: str, content: str) -> str:
    begin, end = f"<!-- AUTO:BEGIN {name} -->", f"<!-- AUTO:END {name} -->"
    if text.count(begin) != 1 or text.count(end) != 1 or text.index(begin) > text.index(end):
        raise SyncError(f"Missing, duplicate or reversed AUTO block: {name}")
    left, rest = text.split(begin, 1)
    _, right = rest.split(end, 1)
    if "<!-- AUTO:" in content:
        raise SyncError("Generated content contains AUTO delimiters")
    return left + begin + "\n" + content.strip() + "\n" + end + right


def block_content(text: str, name: str) -> str:
    match = re.search(
        re.escape(f"<!-- AUTO:BEGIN {name} -->") + r"\n(.*?)\n"
        + re.escape(f"<!-- AUTO:END {name} -->"), text, re.S
    )
    if not match:
        raise SyncError(f"Missing AUTO block: {name}")
    return match.group(1)


def safe_text(value: str) -> str:
    return html.escape(value).replace("\n", " ").replace("\r", " ")


def compact(snapshot: dict) -> dict:
    data = json.loads(json.dumps(snapshot))
    for item in data["documents"].values():
        item.pop("content", None)
        item.pop("previous_content", None)
    return data


def report(config: dict, baseline: dict | None, candidate: dict, delta: dict) -> str:
    tag = safe_text(candidate["latest"]["tag"])
    previous = safe_text(baseline["latest"]["tag"]) if baseline else "首次建立基线"
    lines = [
        f"# {config['name']} 更新报告", "",
        f"比较范围：{previous} → {tag}", "",
        f"采集时间：{candidate['collected_at']}", "",
        "**此报告由自动检测生成，尚未进行人工内容审核或命令实测。**", "",
        "## 发布记录", "",
    ]
    for release in delta["releases"]:
        lines += [
            f"- [{safe_text(release['tag'])}]({release['url']})",
            f"  - 证据编号：release:{release['id']}",
        ]
    if not delta["releases"]:
        lines.append("- 无新稳定版；仍检查现有发布说明及文档修订。")
    lines += ["", "## 文档变化及影响", ""]
    for change in delta["documents"]:
        item, key = change["after"], change["key"]
        label = "稳定版来源" if item["channel"] == "stable" else "开发分支来源，可能尚未发布"
        lines += [
            f"### {key}", "", f"- 渠道：{label}",
            f"- [不可变提交证据]({item['url']})",
            f"- [官方阅读入口]({item['official_url']})",
            f"- 涉及文档：{', '.join(item['targets'])}",
            "- 处理：核对本地步骤；自动化未宣称命令已适配或实测。",
            "",
        ]
        old = change["before"]
        if old:
            before = old.get("content", item.get("previous_content", ""))
            patch = list(difflib.unified_diff(
                before.splitlines(), item["content"].splitlines(), fromfile="accepted",
                tofile="candidate", lineterm=""
            ))
            # Escape HTML/fences from upstream; full snapshots live in run artifacts.
            lines += ["<pre>", html.escape("\n".join(patch[:120])), "</pre>", ""]
            if len(patch) > 120:
                lines += ["差异已截断；请通过提交链接查看完整来源。", ""]
        else:
            lines += ["首次登记该来源，需核对现有教程后接受基线。", ""]
    if delta.get("config_changed"):
        lines += ["来源登记配置已变化，需要同时核对跟踪范围。", ""]
    if not delta["documents"]:
        lines += ["未检测到所登记官方文档的内容变化。", ""]
    lines += [
        "## 检查与审核", "",
        "- 候选检查：运行 docsync check、单元测试和 MkDocs 严格构建；以运行结果为准。",
        "- 人工审核：待完成。",
        "- 命令实测：尚未实测；tested_versions 不自动更新。",
        "- 无需调整的章节可在审核后保留原文，并在 PR 中记录判断。",
        "- 合并接受来源基线；关闭 PR 不推进主分支基线。",
        "- 回滚：撤销本次合并并重新发布。",
        "", f"<!-- docsync-fingerprint:{delta['fingerprint']} -->", "",
    ]
    return "\n".join(lines)


def plan_files(root, config, state, candidate, delta) -> dict[str, str]:
    summary = inside(root, config["release_summary"]).read_text(encoding="utf-8")
    latest = candidate["latest"]
    text = (
        f"- 最近检测到的稳定版：[{safe_text(latest['tag'])}]({latest['url']})\n"
        f"- 官方来源检查时间：{candidate['collected_at']}\n"
        "- 状态：自动采集；内容审核与命令实测请分别查看本文元数据。\n"
        "- 开发分支变化仅作为待核查线索，不代表稳定版已经支持。"
    )
    summary = replace_block(summary, "release-summary", text)
    history = inside(root, config["history"]).read_text(encoding="utf-8")
    previous = block_content(history, "update-history")
    entry = (
        f"- {datetime.now(timezone.utc).date().isoformat()}：登记来源状态 "
        f"[{safe_text(latest['tag'])}]({latest['url']})；"
        f"{len(delta['documents'])} 个来源发生变化。审核与实测状态另行记录。"
    )
    history = replace_block(history, "update-history", entry + "\n" + previous)
    new_state = json.loads(json.dumps(state))
    new_state["tools"][config["id"]] = compact(candidate)
    changes = {
        config["release_summary"]: summary,
        config["history"]: history,
        "state/sources.lock.json": json.dumps(new_state, ensure_ascii=False, indent=2) + "\n",
    }

    targets = {p for item in config["documents"] for p in item["targets"]}
    targets.add(config["release_summary"])
    targets.add(config["history"])
    date = candidate["collected_at"][:10]
    for path in targets:
        text = changes.get(path, inside(root, path).read_text(encoding="utf-8"))
        changes[path] = re.sub(r"(?m)^sources_checked_at:.*$", f"sources_checked_at: {date}", text, count=1)
    return changes
