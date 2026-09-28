"""GitHub readers: the CTO's change-failure rate and CI pass rate, from APIs you already have.

Token: a fine-grained, READ-ONLY token in $GITHUB_TOKEN (Deployments: read, Actions: read).
Inside GitHub Actions the built-in token works with `permissions: {deployments: read, actions: read}`.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from ._http import get_json

API = "https://api.github.com"
FAILED = {"failure", "error"}
FINISHED = {"success", "failure", "error"}


def _headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN", "")
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _since(days: int, now: datetime | None) -> datetime:
    return (now or datetime.now(timezone.utc)) - timedelta(days=days)


def change_failure_rate(repo: str, environment: str = "production", days: int = 30,
                        key: str = "change_failure_rate_pct",
                        now: datetime | None = None) -> Callable[[], dict]:
    """(failed + errored) / finished deployments to `environment` over the window, in percent.

    A deployment's outcome is its LATEST status. Pending / in-progress / queued are not counted.
    """

    def _snapshot() -> dict:
        since = _since(days, now)
        deployments = get_json(f"{API}/repos/{repo}/deployments",
                               params={"environment": environment, "per_page": 100}, headers=_headers())
        finished = failed = 0
        for d in deployments:
            created = datetime.fromisoformat(d["created_at"].replace("Z", "+00:00"))
            if created < since:
                continue
            statuses = get_json(d["statuses_url"], params={"per_page": 1}, headers=_headers())
            state = statuses[0]["state"] if statuses else None
            if state in FINISHED:
                finished += 1
                failed += state in FAILED
        if finished == 0:
            return {"unavailable": f"no finished {environment} deployments in {days}d"}
        return {key: round(100.0 * failed / finished, 1), "deployments": finished, "failed": failed}

    return _snapshot


def ci_pass_rate(repo: str, branch: str = "main", days: int = 7, key: str = "ci_pass_rate_pct",
                 now: datetime | None = None) -> Callable[[], dict]:
    """Share of completed GitHub Actions runs on `branch` that concluded "success"."""

    def _snapshot() -> dict:
        since = _since(days, now).strftime("%Y-%m-%d")
        data = get_json(f"{API}/repos/{repo}/actions/runs",
                        params={"branch": branch, "status": "completed", "created": f">={since}",
                                "per_page": 100}, headers=_headers())
        runs = [r for r in data.get("workflow_runs", []) if r.get("conclusion") in ("success", "failure")]
        if not runs:
            return {"unavailable": f"no completed runs on {branch} in {days}d"}
        passed = sum(r["conclusion"] == "success" for r in runs)
        return {key: round(100.0 * passed / len(runs), 1), "runs": len(runs)}

    return _snapshot
