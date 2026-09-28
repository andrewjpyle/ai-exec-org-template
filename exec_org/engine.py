"""The one engine. A single job loops every armed seat and writes ONE draft brief.

One engine, not seven: every seat plugs into the same loop, so there is one schedule to
watch, one failure mode, and one place to hang the dead-man.

The engine only WRITES A DRAFT to a sink a human reads. It has no code path that sends,
spends, merges or changes anything.

Each brief ends with an invisible marker, ``<!-- exec-metrics:v1 {...} -->``. The next
run reads it back from the previous brief to print day-over-day deltas.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from .arbitration import one_action
from .registry import Seat, armed_seats, fix_first, headline, safe_snapshot
from .sinks import BriefSink, FileSink

MARKER_RE = re.compile(r"<!-- exec-metrics:v1 (\{.*?\}) -->", re.DOTALL)

Narrator = Callable[[Seat, dict], list[str]]


def _fmt(v) -> str:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return str(v)
    return f"{int(v):,}" if float(v).is_integer() else f"{v:,.2f}".rstrip("0").rstrip(".")


def previous_metrics(body: str | None) -> dict:
    """Parse the metrics marker out of a previous brief. Missing or broken → {}."""
    if not body:
        return {}
    m = MARKER_RE.search(body)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}


def delta_text(seat: Seat, value, prev) -> str:
    if not isinstance(value, (int, float)) or not isinstance(prev, (int, float)):
        return "(no prior reading)"
    diff = value - prev
    if diff == 0:
        return "(= flat vs last brief)"
    good = (diff > 0) == (seat.better == "up")
    arrow = "▲" if diff > 0 else "▼"
    return f"({arrow} {'+' if diff > 0 else ''}{_fmt(diff)}{seat.unit} vs last brief, {'better' if good else 'worse'})"


def compose_brief(env: dict | None = None, now: datetime | None = None,
                  previous: str | None = None, narrator: Narrator | None = None,
                  precedence: Sequence[str] | None = None) -> str | None:
    """Return the markdown brief for all armed seats, or None if none are armed."""
    seats = armed_seats(env)
    if not seats:
        return None
    now = now or datetime.now(timezone.utc)
    readings = [(seat, safe_snapshot(seat)) for seat in seats]
    prev = previous_metrics(previous)
    decision = one_action(readings, precedence)

    lines = [f"# AI Executive Daily Brief (DRAFT) · {now:%Y-%m-%d}", "",
             "> Draft only. Nothing in this brief has been executed. A human reads it and decides.", "",
             "## Today's one action", "", f"**{decision.action}**", ""]
    lines.append(f"_Owner: {decision.owner}. Why: {decision.why}._" if decision.owner
                 else f"_Why: {decision.why}._")
    lines.append("")

    metrics = {}
    for seat, snap in readings:
        value = headline(seat, snap)
        lines.append(f"## {seat.title}")
        lines.append(f"_Owns: {seat.owned_outcome}_")
        lines.append("")
        if value is None:
            lines.append(f"- **{seat.number}**: unavailable ({snap.get('unavailable', 'unknown')})")
        else:
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                metrics[seat.role_id] = value
            lines.append(f"- **{seat.number}**: {_fmt(value)}{seat.unit} "
                         f"{delta_text(seat, value, prev.get(seat.role_id))}")
        for key, extra in snap.items():
            if key not in (seat.number, "unavailable"):
                lines.append(f"  - {key}: {_fmt(extra)}")
        if seat.alarm is None:
            lines.append("- Fix first: no alarm set for this seat")
        elif value is None:
            lines.append("- Fix first: blind (the number is unreadable, so the alarm cannot be judged)")
        else:
            lines.append(f"- Fix first: {fix_first(seat, snap) or f'nothing. Alarm fires at {seat.alarm}{seat.unit}'}")
        if narrator is not None and value is not None:
            read = narrator(seat, snap)
            if read:
                lines.append("- Claude's read (advisory, numbers checked against the snapshot):")
                lines.extend(f"  - {r}" for r in read)
        lines.append("")

    lines.append(f"<!-- exec-metrics:v1 {json.dumps(metrics, sort_keys=True)} -->")
    return "\n".join(lines)


def run_daily_brief(sink: BriefSink | None = None, env: dict | None = None,
                    narrator: Narrator | None = None,
                    precedence: Sequence[str] | None = None) -> dict:
    """Compose and deliver today's draft. Self-silences when no seat is armed."""
    sink = sink or FileSink()
    try:
        last = sink.latest()
    except Exception:  # a sink that cannot be read still gets today's brief, just no deltas
        last = None
    body = compose_brief(env, previous=last[1] if last else None,
                         narrator=narrator, precedence=precedence)
    if body is None:
        return {"written": False, "reason": "no seats armed"}
    title = f"AI Executive Daily Brief (DRAFT) · {datetime.now(timezone.utc):%Y-%m-%d}"
    location = sink.write(body, title)
    return {"written": True, "location": location,
            "armed": [s.role_id for s in armed_seats(env)]}
