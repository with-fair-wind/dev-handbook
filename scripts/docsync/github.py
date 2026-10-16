"""Publish one review branch using non-forced Git refs and immutable base checks."""
import hashlib
import json
import re
import subprocess

from .config import SyncError

BOT = {"name": "dev-handbook[bot]", "email": "41898282+github-actions[bot]@users.noreply.github.com"}


def run(args, root=None, stdin=None):
    result = subprocess.run(args, cwd=root, input=stdin, text=True, encoding="utf-8", capture_output=True)
    if result.returncode:
        # Raw CLI errors may contain user-supplied payloads; do not echo credentials.
        raise SyncError(f"Command failed: {args[0]} {args[1]}")
    return result.stdout.strip()


class Publisher:
    def __init__(self, root, repository, tool):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise SyncError("Invalid destination repository")
        self.root, self.repository = root, repository
        self.branch = f"automation/{tool}"
        self.tool = tool

    def api(self, endpoint, method="GET", data=None, optional=False):
        args = ["gh", "api", endpoint, "--method", method]
        if data is not None:
            args += ["--input", "-"]
        result = subprocess.run(
            args, input=json.dumps(data) if data is not None else None,
            text=True, encoding="utf-8", capture_output=True
        )
        if result.returncode:
            if optional:
                try:
                    if json.loads(result.stdout).get("status") == "404":
                        return None
                except (ValueError, AttributeError):
                    pass
            raise SyncError(f"GitHub {method} failed: {endpoint.split('?')[0]}")
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def endpoint(self, tail):
        return f"repos/{self.repository}/{tail}"

    def inspect(self, key):
        repo = self.api(f"repos/{self.repository}")
        self.base_branch = repo["default_branch"]
        self.base_sha = self.api(self.endpoint(f"git/ref/heads/{self.base_branch}"))["object"]["sha"]
        if run(["git", "rev-parse", "HEAD"], self.root) != self.base_sha:
            raise SyncError("Local HEAD differs from remote default branch; refresh checkout")
        if run(["git", "status", "--porcelain", "--untracked-files=normal"], self.root):
            raise SyncError("Publish needs a clean checkout")
        owner = self.repository.split("/")[0]
        pulls = self.api(self.endpoint(f"pulls?state=all&head={owner}:{self.branch}&per_page=100"))
        if len(pulls) == 100:
            raise SyncError("Too many matching PRs; manual branch review required")
        self.pr = next((p for p in pulls if p["state"] == "open"), None)
        for item in pulls:
            if f"<!-- docsync-key:{key} -->" in (item.get("body") or ""):
                return {"skip": True, "url": item["html_url"], "reason": "相同候选已提交或已关闭"}
        ref = self.api(self.endpoint(f"git/ref/heads/{self.branch}"), optional=True)
        self.head_sha = ref["object"]["sha"] if ref else None
        if self.head_sha and self.head_sha != self.base_sha:
            comparison = self.api(self.endpoint(f"compare/{self.base_sha}...{self.head_sha}"))
            if comparison["total_commits"] > 200:
                raise SyncError("Automation branch history needs manual review")
            for commit in comparison["commits"]:
                details = commit["commit"]
                if details["author"]["name"] != BOT["name"] or details["committer"]["name"] != BOT["name"]:
                    raise SyncError("Human changes on automation branch; refusing to overwrite")
        return {"skip": False}

    def publish(self, changes, title, body, key):
        if self.api(self.endpoint(f"git/ref/heads/{self.base_branch}"))["object"]["sha"] != self.base_sha:
            raise SyncError("Default branch changed during generation; retry on fresh checkout")
        current = self.api(self.endpoint(f"git/ref/heads/{self.branch}"), optional=True)
        actual = current["object"]["sha"] if current else None
        if actual != self.head_sha:
            raise SyncError("Automation branch changed during generation")
        base_commit = self.api(self.endpoint(f"git/commits/{self.base_sha}"))
        tree = self.api(self.endpoint("git/trees"), "POST", {
            "base_tree": base_commit["tree"]["sha"],
            "tree": [
                {"path": path, "mode": "100644", "type": "blob", "content": content}
                for path, content in sorted(changes.items())
            ],
        })
        parents = list(dict.fromkeys([self.head_sha, self.base_sha])) if self.head_sha else [self.base_sha]
        commit = self.api(self.endpoint("git/commits"), "POST", {
            "message": title, "tree": tree["sha"], "parents": parents,
            "author": BOT, "committer": BOT,
        })
        if self.head_sha:
            self.api(self.endpoint(f"git/refs/heads/{self.branch}"), "PATCH", {"sha": commit["sha"], "force": False})
        else:
            self.api(self.endpoint("git/refs"), "POST", {"ref": f"refs/heads/{self.branch}", "sha": commit["sha"]})
        pr_body = body[:45000] + f"\n\n<!-- docsync-key:{key} -->\n"
        data = {"title": title, "body": pr_body, "base": self.base_branch}
        if self.pr:
            result = self.api(self.endpoint(f"pulls/{self.pr['number']}"), "PATCH", data)
        else:
            result = self.api(self.endpoint("pulls"), "POST", {**data, "head": self.branch, "draft": False})
        return result["html_url"]

    def failure(self, message):
        title = f"docsync: {self.tool} 自动更新需要处理"
        issues = self.api(self.endpoint("issues?state=open&per_page=100"))
        existing = next((i for i in issues if "pull_request" not in i and i["title"] == title), None)
        marker = hashlib.sha256(message.encode()).hexdigest()
        body = f"自动更新未完成，已保留主分支内容和已接受基线。\n\n原因：{message}\n\n请检查 Actions 运行记录，修复后手动重试。\n\n<!-- failure:{marker} -->"
        if existing:
            if f"<!-- failure:{marker} -->" not in (existing.get("body") or ""):
                self.api(self.endpoint(f"issues/{existing['number']}"), "PATCH", {"body": body})
        else:
            self.api(self.endpoint("issues"), "POST", {"title": title, "body": body})

    def recovered(self):
        title = f"docsync: {self.tool} 自动更新需要处理"
        for issue in self.api(self.endpoint("issues?state=open&per_page=100")):
            if "pull_request" not in issue and issue["title"] == title:
                self.api(self.endpoint(f"issues/{issue['number']}"), "PATCH", {"state": "closed", "state_reason": "completed"})
