"""Where a draft brief lands. Every sink is a place a HUMAN READS, never a place that acts.

A sink implements two methods:
    write(body, title) -> str                  where it landed (path / URL)
    latest() -> (datetime, body) | None         the most recent brief, for deltas + the dead-man

    FileSink          markdown files in a folder (default)
    GitHubIssueSink   one issue per day, labeled `exec-brief`
    SlackSink         posts to a webhook (write-only: pair it with another sink via MultiSink)
    MultiSink         write everywhere, read `latest()` from the first sink
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from ..readers._http import USER_AGENT, get_json

Latest = tuple[datetime, str] | None


class BriefSink(Protocol):
    def write(self, body: str, title: str) -> str: ...
    def latest(self) -> Latest: ...


def _post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST", headers={
        "Content-Type": "application/json", "User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as resp:
        raw = resp.read().decode("utf-8")
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        return {"raw": raw}


class FileSink:
    """Writes briefs/brief_YYYY-MM-DD.md. Re-running the same day overwrites that day's file."""

    def __init__(self, directory: str | None = None):
        self.directory = Path(directory or os.environ.get("EXEC_BRIEF_DIR", "briefs"))

    def write(self, body: str, title: str = "") -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"brief_{datetime.now(timezone.utc):%Y-%m-%d}.md"
        path.write_text(body, encoding="utf-8")
        return str(path)

    def latest(self) -> Latest:
        files = sorted(self.directory.glob("brief_*.md")) if self.directory.exists() else []
        if not files:
            return None
        newest = max(files, key=lambda f: f.stat().st_mtime)
        return (datetime.fromtimestamp(newest.stat().st_mtime, tz=timezone.utc),
                newest.read_text(encoding="utf-8"))


class GitHubIssueSink:
    """One issue per brief in `repo`, labeled `exec-brief`. Needs $GITHUB_TOKEN with issues: write."""

    API = "https://api.github.com"

    def __init__(self, repo: str | None = None, label: str = "exec-brief"):
        self.repo = repo or os.environ.get("EXEC_GITHUB_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
        self.label = label
        if not self.repo:
            raise ValueError("GitHubIssueSink needs a repo (owner/name) or $GITHUB_REPOSITORY")

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
                "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    def write(self, body: str, title: str) -> str:
        issue = _post_json(f"{self.API}/repos/{self.repo}/issues",
                           {"title": title, "body": body, "labels": [self.label]}, self._headers())
        return issue.get("html_url", "")

    def latest(self) -> Latest:
        issues = get_json(f"{self.API}/repos/{self.repo}/issues",
                          params={"labels": self.label, "state": "all", "sort": "created",
                                  "direction": "desc", "per_page": 1}, headers=self._headers())
        if not issues:
            return None
        created = datetime.fromisoformat(issues[0]["created_at"].replace("Z", "+00:00"))
        return created, issues[0].get("body") or ""


class SlackSink:
    """Posts the brief to a Slack incoming webhook (URL in $EXEC_SLACK_WEBHOOK). Write-only."""

    def __init__(self, webhook_env: str = "EXEC_SLACK_WEBHOOK"):
        self.url = os.environ.get(webhook_env, "")
        if not self.url:
            raise ValueError(f"SlackSink needs ${webhook_env}")

    def write(self, body: str, title: str = "") -> str:
        _post_json(self.url, {"text": f"*{title}*\n{body}" if title else body})
        return "slack"

    def latest(self) -> Latest:
        return None


class MultiSink:
    """Write to several sinks; `latest()` comes from the first one (keep a readable one first)."""

    def __init__(self, *sinks):
        if not sinks:
            raise ValueError("MultiSink needs at least one sink")
        self.sinks = sinks

    def write(self, body: str, title: str = "") -> str:
        return ", ".join(s.write(body, title) for s in self.sinks)

    def latest(self) -> Latest:
        return self.sinks[0].latest()


def from_env(name: str | None = None) -> BriefSink:
    """Pick a sink by name: file (default), github, slack, or a comma list like "file,slack"."""
    name = (name or os.environ.get("EXEC_SINK", "file")).strip().lower()
    build = {"file": FileSink, "github": GitHubIssueSink, "slack": SlackSink}
    parts = [p.strip() for p in name.split(",") if p.strip()]
    unknown = [p for p in parts if p not in build]
    if unknown:
        raise ValueError(f"unknown sink(s) {unknown}; choose from {sorted(build)}")
    sinks = [build[p]() for p in parts]
    return sinks[0] if len(sinks) == 1 else MultiSink(*sinks)


__all__ = ["BriefSink", "FileSink", "GitHubIssueSink", "SlackSink", "MultiSink", "from_env"]
