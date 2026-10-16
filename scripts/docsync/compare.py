"""Compare against the merged baseline; timestamps/commit-only changes are noise."""
import hashlib
import json


def fingerprint(snapshot: dict) -> str:
    stable = {
        "latest": snapshot["latest"], "config_hash": snapshot.get("config_hash"),
        "documents": {k: v["hash"] for k, v in sorted(snapshot["documents"].items())},
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def compare(baseline: dict | None, candidate: dict) -> dict:
    old_docs = baseline["documents"] if baseline else {}
    changes = []
    for key, item in candidate["documents"].items():
        old = old_docs.get(key)
        if old is None or old["hash"] != item["hash"]:
            changes.append({"key": key, "before": old, "after": item})
    latest_changed = not baseline or baseline["latest"] != candidate["latest"]
    previous = baseline["latest"]["id"] if baseline else None
    releases = [r for r in candidate["releases"] if r["id"] != previous]
    if latest_changed and previous == candidate["latest"]["id"]:
        releases = [candidate["latest"]]
    config_changed = not baseline or baseline.get("config_hash") != candidate.get("config_hash")
    return {
        "config_changed": config_changed,
        "bootstrap": baseline is None,
        "changed": latest_changed or bool(changes) or config_changed,
        "latest_changed": latest_changed,
        "documents": changes,
        "releases": releases if latest_changed else [],
        "fingerprint": fingerprint(candidate),
    }
