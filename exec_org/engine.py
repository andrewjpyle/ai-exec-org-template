"""The one engine. A single job loops every armed seat and writes ONE draft brief.

One engine, not seven: every seat plugs into the same loop, so there is one
schedule to watch, one failure mode, and one place to add the dead-man.

The engine only WRITES A DRAFT. It has no code path that sends, spends, merges
or changes anything. A human reads the brief and decides.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .registry import armed_seats, safe_snapshot
from .sinks import BriefSink, FileSink


def compose_brief(env: Optional[dict] = None, now: Optional[datetime] = None) -> Optional[str]:
    """Return the markdown brief for all armed seats, or None if none are armed."""
    seats = armed_seats(env)
    if not seats:
        return None
    now = now or datetime.now(timezone.utc)
    lines = [f"# AI Executive Daily Brief (DRAFT) {now:%Y-%m-%d}", "",
             "_Draft only. Nothing in this brief has been executed._", ""]
    for seat in seats:
        snap = safe_snapshot(seat)
        lines.append(f"## {seat.title}: {seat.owned_outcome}")
        lines.append(f"- **the number**: `{seat.number}`")
        if "unavailable" in snap:
            lines.append(f"- _unavailable: {snap['unavailable']}_")
        else:
            for key, value in snap.items():
                lines.append(f"- **{key}**: {value}")
        lines.append("")
    return "\n".join(lines)


def run_daily_brief(sink: Optional[BriefSink] = None, env: Optional[dict] = None) -> dict:
    """Compose and deliver today's draft. Self-silences when no seat is armed."""
    body = compose_brief(env)
    if body is None:
        return {"written": False, "reason": "no seats armed"}
    sink = sink or FileSink()
    location = sink.write(body)
    return {"written": True, "location": location,
            "armed": [s.role_id for s in armed_seats(env)]}
