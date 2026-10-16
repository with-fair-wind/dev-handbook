import base64
import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docsync.ai import generate
from docsync.cli import update
from docsync.collect import collect, digest
from docsync.compare import compare, fingerprint
from docsync.config import SyncError, inside, load_config
from docsync.github import BOT, Publisher
from docsync.render import compact, plan_files, replace_block
from docsync.validate import check_repository, validate_changes

PROJECT = Path(__file__).resolve().parents[1]


def release(number=2, pre=False, draft=False):
    return {
        "id": number, "tag_name": f"v{number}.0.0", "html_url": f"https://github.com/example/tool/releases/tag/v{number}.0.0",
        "published_at": "2026-10-16T00:00:00Z", "body": f"Release {number}",
        "prerelease": pre, "draft": draft,
    }


class FakeAPI:
    def __init__(self, number=2):
        self.number = number
        self.text = "Official installation instructions and configuration.\n"
        self.releases = [release(number), release(1)]
        self.fail_path = None
        self.stable_sha, self.preview_sha = "b" * 40, "a" * 40
        self.contents = {}

    def get(self, path):
        if self.fail_path and self.fail_path in path:
            raise SyncError("Source unavailable")
        if path.endswith("/releases/latest"):
            return release(self.number)
        if "/releases?" in path:
            return self.releases
        if "/commits/" in path:
            return {"sha": self.preview_sha if "main" in path else self.stable_sha}
        if "/contents/" in path:
            return {"type": "file", "encoding": "base64", "content": base64.b64encode(self.contents.get(path.split("?ref=")[-1], self.text).encode()).decode()}
        raise AssertionError(path)


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ("docs", "sources", "state"):
            shutil.copytree(PROJECT / name, self.root / name)
        shutil.copy2(PROJECT / "mkdocs.yml", self.root / "mkdocs.yml")
        self.config = load_config(self.root, "oh-my-posh")
        self.api = FakeAPI()
        self.snapshot = collect(self.config, None, self.api)

    def test_first_registration_has_both_channels(self):
        delta = compare(None, self.snapshot)
        self.assertTrue(delta["bootstrap"])
        self.assertEqual(len(delta["documents"]), 10)
        self.assertEqual(len(delta["releases"]), 1)

    def test_timestamp_and_commit_only_changes_do_not_create_updates(self):
        other = copy.deepcopy(self.snapshot)
        other["collected_at"] = "2099-01-01T00:00:00Z"
        for doc in other["documents"].values():
            doc["commit"] = "c" * 40
        self.assertFalse(compare(self.snapshot, other)["changed"])
        self.assertEqual(fingerprint(other), fingerprint(self.snapshot))

    def test_doc_only_change_detected_without_release(self):
        other = copy.deepcopy(self.snapshot)
        other["documents"]["preview:prompt"]["content"] += "New behavior\n"
        other["documents"]["preview:prompt"]["hash"] = digest(other["documents"]["preview:prompt"]["content"])
        result = compare(self.snapshot, other)
        self.assertTrue(result["changed"])
        self.assertFalse(result["latest_changed"])
        self.assertEqual(result["documents"][0]["key"], "preview:prompt")

    def test_config_change_is_detected(self):
        other = copy.deepcopy(self.snapshot)
        other["config_hash"] = "different"
        self.assertTrue(compare(self.snapshot, other)["config_changed"])

    def test_multiple_releases_and_previews(self):
        baseline = copy.deepcopy(self.snapshot)
        baseline["latest"] = {k: v for k, v in self.snapshot["latest"].items()}
        baseline["latest"]["id"] = 1
        self.api.number = 4
        self.api.releases = [release(4), release(5, pre=True), release(3), release(9, draft=True), release(2), release(1)]
        candidate = collect(self.config, baseline, self.api)
        self.assertEqual([r["id"] for r in candidate["releases"]], [4, 3, 2])

    def test_missing_baseline_fails_closed(self):
        baseline = copy.deepcopy(self.snapshot)
        baseline["latest"]["id"] = 999
        self.api.number = 4
        with self.assertRaises(SyncError):
            collect(self.config, baseline, self.api)

    def test_partial_source_failure_does_not_advance_state(self):
        before = (self.root / "state/sources.lock.json").read_bytes()
        self.api.fail_path = "fonts.mdx"
        with self.assertRaises(SyncError):
            collect(self.config, self.snapshot, self.api)
        self.assertEqual(before, (self.root / "state/sources.lock.json").read_bytes())

    def test_empty_source_is_not_a_deletion(self):
        self.api.text = ""
        with self.assertRaises(SyncError):
            collect(self.config, self.snapshot, self.api)

    def test_compact_baseline_reconstructs_unchanged_metadata(self):
        baseline = compact(self.snapshot)
        self.assertNotIn("content", baseline["documents"]["stable:windows"])
        self.assertFalse(compare(baseline, collect(self.config, baseline, self.api))["changed"])

    def test_changed_source_reconstructed_from_accepted_commit(self):
        baseline = compact(self.snapshot)
        self.api.contents = {"b" * 40: self.api.text, "a" * 40: self.api.text}
        self.api.stable_sha, self.api.preview_sha = "c" * 40, "d" * 40
        self.api.text += "New official behavior.\n"
        candidate = collect(self.config, baseline, self.api)
        self.assertEqual(len(compare(baseline, candidate)["documents"]), 10)
        self.assertEqual(candidate["documents"]["stable:windows"]["previous_content"],
                         self.snapshot["documents"]["stable:windows"]["content"])

    def test_release_note_revision_has_evidence(self):
        other = copy.deepcopy(self.snapshot)
        other["latest"]["body"] += " Revised."
        delta = compare(self.snapshot, other)
        self.assertTrue(delta["changed"])
        self.assertEqual(delta["releases"][0]["id"], other["latest"]["id"])

    def test_pagination_keeps_intermediate_releases(self):
        baseline = copy.deepcopy(self.snapshot)
        baseline["latest"]["id"] = 1
        self.api.number = 102
        original_get = self.api.get
        def get(path):
            if "/releases?" in path:
                return [release(i) for i in range(102, 2, -1)] if "&page=1" in path else [release(2), release(1)]
            return original_get(path)
        self.api.get = get
        result = collect(self.config, baseline, self.api)
        self.assertEqual(len(result["releases"]), 101)

    def test_wrong_previous_checksum_blocks_update(self):
        baseline = compact(self.snapshot)
        self.api.text += "Changed.\n"
        with self.assertRaisesRegex(SyncError, "checksum"):
            collect(self.config, baseline, self.api)

    def test_personal_content_and_tested_versions_are_preserved(self):
        state = {"schema_version": 1, "tools": {}}
        changes = plan_files(self.root, self.config, state, self.snapshot, compare(None, self.snapshot))
        validate_changes(self.root, self.config, changes)
        for path, content in changes.items():
            if path.endswith(".md"):
                self.assertIn("tested_versions: []", content)
                self.assertIn("content_reviewed_at: null", content)
        path = self.config["release_summary"]
        changes[path] += "\nUnrequested personal rewrite"
        with self.assertRaises(SyncError):
            validate_changes(self.root, self.config, changes)

    def test_metadata_cannot_claim_testing(self):
        path = self.config["release_summary"]
        content = (self.root / path).read_text(encoding="utf-8").replace("tested_versions: []", "tested_versions: [v100]")
        with self.assertRaises(SyncError):
            validate_changes(self.root, self.config, {path: content})

    def test_auto_marker_failure(self):
        for text in ("No markers", "<!-- AUTO:BEGIN x -->\n<!-- AUTO:BEGIN x -->\n<!-- AUTO:END x -->"):
            with self.assertRaises(SyncError):
                replace_block(text, "x", "generated")

    def test_path_traversal_is_rejected(self):
        for path in ("../outside", "/absolute", "C:/outside", "docs/../../outside", "docs\\outside"):
            with self.assertRaises(SyncError):
                inside(self.root, path)

    def test_symlink_escape_is_rejected(self):
        # Symlink privileges vary on Windows; traversal checks above always run.
        link = self.root / "escape"
        try:
            link.symlink_to(self.root.parent, target_is_directory=True)
        except OSError:
            self.skipTest("Symlink creation not permitted")
        with self.assertRaises(SyncError):
            inside(self.root, "escape/outside.md")

    def test_preview_apply_and_repeat(self):
        fixture = self.root / "fixture.json"
        fixture.write_text(json.dumps(self.snapshot), encoding="utf-8")
        initial = (self.root / "state/sources.lock.json").read_bytes()
        result = update(self.root, "oh-my-posh", fixture=fixture)
        self.assertTrue(result["changed"])
        self.assertEqual(initial, (self.root / "state/sources.lock.json").read_bytes())
        update(self.root, "oh-my-posh", fixture=fixture, apply=True)
        self.assertFalse(update(self.root, "oh-my-posh", fixture=fixture)["changed"])
        self.assertEqual(check_repository(self.root), 13)

    def test_incomplete_snapshot_rejected(self):
        del self.snapshot["documents"]["stable:windows"]
        fixture = self.root / "fixture.json"
        fixture.write_text(json.dumps(self.snapshot), encoding="utf-8")
        with self.assertRaises(SyncError):
            update(self.root, "oh-my-posh", fixture=fixture, apply=True)

    def test_fixtures_cannot_be_published(self):
        with self.assertRaises(SyncError):
            update(self.root, "oh-my-posh", fixture="anything", publish=True, repository="owner/repo")

    def test_optional_ai_missing_is_a_successful_fallback(self):
        with patch.dict(os.environ, {}, clear=True):
            result, note = generate(self.root, self.config, self.snapshot, compare(None, self.snapshot), {})
        self.assertEqual(result, {})
        self.assertIn("未配置", note)

    def test_invalid_ai_endpoint_falls_back(self):
        with patch.dict(os.environ, {"DOCSYNC_AI_URL": "http://example.org"}):
            result, note = generate(self.root, self.config, self.snapshot, compare(None, self.snapshot), {})
        self.assertEqual(result, {})
        self.assertIn("降级", note)

    def test_invalid_ai_evidence_cannot_modify_files(self):
        path = self.config["documents"][0]["targets"][0]
        with patch.dict(os.environ, {"DOCSYNC_AI_URL": "https://example.org/generate"}):
            result, note = generate(
                self.root, self.config, self.snapshot, compare(None, self.snapshot), {},
                requester=lambda _: {"changes": [{"path": path, "content": "claim", "evidence": ["invented"]}]}
            )
        self.assertEqual(result, {})
        self.assertIn("降级", note)

    def test_valid_preview_ai_note_is_labelled(self):
        path = self.config["documents"][0]["targets"][0]
        with patch.dict(os.environ, {"DOCSYNC_AI_URL": "https://example.org/generate"}):
            result, _ = generate(
                self.root, self.config, self.snapshot, compare(None, self.snapshot), {},
                requester=lambda _: {"changes": [{"path": path, "content": "核查变化", "evidence": ["preview:windows"]}]}
            )
        self.assertIn("可能尚未发布", result[path])
        validate_changes(self.root, self.config, result)

    def test_ai_cannot_choose_other_files(self):
        with patch.dict(os.environ, {"DOCSYNC_AI_URL": "https://example.org/generate"}):
            result, _ = generate(
                self.root, self.config, self.snapshot, compare(None, self.snapshot), {},
                requester=lambda _: {"changes": [{"path": ".github/workflows/evil.yml", "content": "claim", "evidence": ["stable:windows"]}]}
            )
        self.assertEqual(result, {})

    def test_human_commit_on_automation_branch_is_protected(self):
        publisher = Publisher(self.root, "owner/repo", "oh-my-posh")
        def api(endpoint, *args, **kwargs):
            if endpoint == "repos/owner/repo":
                return {"default_branch": "main"}
            if "git/ref/heads/main" in endpoint:
                return {"object": {"sha": "base"}}
            if "pulls?" in endpoint:
                return [{"state": "open", "number": 1, "body": "", "html_url": "url"}]
            if "git/ref/heads/automation/" in endpoint:
                return {"object": {"sha": "head"}}
            if "compare/" in endpoint:
                return {"total_commits": 1, "commits": [{"commit": {"author": {"name": "human"}, "committer": BOT}}]}
            raise AssertionError(endpoint)
        publisher.api = api
        with patch("docsync.github.run", side_effect=["base", ""]):
            with self.assertRaisesRegex(SyncError, "Human changes"):
                publisher.inspect("key")

    def test_closed_matching_pr_is_not_reopened(self):
        publisher = Publisher(self.root, "owner/repo", "oh-my-posh")
        def api(endpoint, *args, **kwargs):
            if endpoint == "repos/owner/repo":
                return {"default_branch": "main"}
            if "git/ref/" in endpoint:
                return {"object": {"sha": "base"}}
            return [{"state": "closed", "number": 1, "body": "<!-- docsync-key:key -->", "html_url": "url"}]
        publisher.api = api
        with patch("docsync.github.run", side_effect=["base", ""]):
            result = publisher.inspect("key")
        self.assertTrue(result["skip"])

    def test_branch_race_stops_before_writes(self):
        publisher = Publisher(self.root, "owner/repo", "oh-my-posh")
        publisher.base_branch, publisher.base_sha, publisher.head_sha = "main", "base", "old"
        publisher.api = lambda endpoint, *args, **kwargs: {"object": {"sha": "base" if endpoint.endswith("/main") else "concurrent"}}
        with self.assertRaisesRegex(SyncError, "changed during"):
            publisher.publish({}, "title", "body", "key")


if __name__ == "__main__":
    unittest.main()
