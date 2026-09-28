"""Two dead-man alarms. They run on their OWN schedule and alert on their OWN
channel, because an alarm that shares a queue with the thing it watches goes
down with it.

1. check_brief_stalled: seats are armed but no brief has landed in 26 hours.
   The engine, its scheduler or its worker has quietly stopped.
2. check_unarmed: seats were built but nobody armed them by the date you set.
   Built-but-never-switched-on is its own kind of silent failure.

Both are quiet by construction when there is nothing wrong.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from .registry import Registry, armed_seats, is_armed
from .sinks import BriefSink, FileSink

MAX_BRIEF_AGE_HOURS = 26  # a daily job plus slack, so a late run is not a false alarm


def check_brief_stalled(sink: Optional[BriefSink] = None, env: Optional[dict] = None,
                        now: Optional[datetime] = None) -> Optional[str]:
    seats = armed_seats(env)
    if not seats:
        return None  # nothing armed means no brief is expected, not a stall
    now = now or datetime.now(timezone.utc)
    last = (sink or FileSink()).latest_written_at()
    if last and now - last < timedelta(hours=MAX_BRIEF_AGE_HOURS):
        return None
    age = "never" if last is None else f"{(now - last).total_seconds() / 3600:.0f}h ago"
    return (f"Exec brief STALLED: {len(seats)} seat(s) armed, last brief {age}. "
            f"Check the scheduler and worker. Armed: {', '.join(s.role_id for s in seats)}")


def check_unarmed(env: Optional[dict] = None, today: Optional[date] = None) -> Optional[str]:
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


def alert(message: str) -> None:
    """Send an alert on a channel separate from the brief. Webhook if set, else stderr."""
    url = os.environ.get("EXEC_ALERT_WEBHOOK", "").strip()
    if url:
        req = urllib.request.Request(url, data=json.dumps({"text": message}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    else:
        print(f"ALERT: {message}", file=sys.stderr)
