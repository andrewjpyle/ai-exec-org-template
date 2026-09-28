"""Two dead-man alarms. They run on their OWN schedule and alert on their OWN channel,
because an alarm that shares a queue with the thing it watches goes down with it.

1. check_brief_stalled: seats are armed but no brief has landed in 26 hours.
   The engine, its scheduler or its worker has quietly stopped.
2. check_unarmed: seats were built but nobody armed them by the date you set.
   Built-but-never-switched-on is its own kind of silent failure.

Both are quiet by construction when there is nothing wrong.
"""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone

from .registry import Registry, armed_seats, is_armed
from .sinks import BriefSink, FileSink, _post_json

MAX_BRIEF_AGE_HOURS = 26  # a daily job plus slack, so a late run is not a false alarm


def check_brief_stalled(sink: BriefSink | None = None, env: dict | None = None,
                        now: datetime | None = None) -> str | None:
    seats = armed_seats(env)
    if not seats:
        return None  # nothing armed means no brief is expected, not a stall
    now = now or datetime.now(timezone.utc)
    try:
        last = (sink or FileSink()).latest()
    except Exception as exc:  # cannot even read the sink: that is itself worth an alert
        return f"Exec brief dead-man cannot read the brief sink ({type(exc).__name__}). Treat as stalled."
    if last and now - last[0] < timedelta(hours=MAX_BRIEF_AGE_HOURS):
        return None
    age = "never" if last is None else f"{(now - last[0]).total_seconds() / 3600:.0f}h ago"
    return (f"Exec brief STALLED: {len(seats)} seat(s) armed, last brief {age}. "
            f"Check the scheduler and worker. Armed: {', '.join(s.role_id for s in seats)}")


def check_unarmed(env: dict | None = None, today: date | None = None) -> str | None:
    env = os.environ if env is None else env
    arm_by = env.get("EXEC_ARM_BY", "").strip()
    if not arm_by:
        return None  # no deadline set, stay quiet
    today = today or date.today()
    if today < date.fromisoformat(arm_by):
        return None
    unarmed = [s.role_id for s in Registry.all() if not is_armed(s, env)]
    if not unarmed:
        return None
    return f"Exec seats built but not armed after {arm_by}: {', '.join(unarmed)}"


def alert(message: str) -> str:
    """Alert on a channel SEPARATE from the brief sink.

    $EXEC_ALERT_WEBHOOK (Slack-compatible) wins; else $EXEC_ALERT_GITHUB_REPO opens an issue
    labeled `exec-alert`; else stderr (which a scheduler's failure email will surface).
    """
    url = os.environ.get("EXEC_ALERT_WEBHOOK", "").strip()
    if url:
        _post_json(url, {"text": message})
        return "webhook"
    repo = os.environ.get("EXEC_ALERT_GITHUB_REPO", "").strip()
    if repo:
        _post_json(f"https://api.github.com/repos/{repo}/issues",
                   {"title": f"Exec org alert · {date.today():%Y-%m-%d}", "body": message,
                    "labels": ["exec-alert"]},
                   {"Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
                    "Accept": "application/vnd.github+json"})
        return "github-issue"
    print(f"ALERT: {message}", file=sys.stderr)
    return "stderr"
