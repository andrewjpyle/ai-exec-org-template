"""Optional: Claude writes a 2-3 line "so what" under each seat's number.

Off unless EXEC_CLAUDE_NARRATE=1 and the `anthropic` package is installed
(`pip install "ai-exec-org-template[claude]"`). Credentials resolve the SDK's normal way
(ANTHROPIC_API_KEY, or an `ant auth login` profile).

Three boundaries, enforced in CODE, not in the prompt:
  1. No tools. The request has no `tools` parameter, so Claude can only return text.
  2. Grounded numbers. Every number Claude writes must appear in that seat's snapshot (or
     its alarm). A line with any other number is DROPPED before it reaches the brief.
  3. Advisory. The brief labels these lines as Claude's read. The seat's number, delta and
     fix-first line are computed by code and never depend on the model.

A failure (no key, refusal, network) never breaks the brief: the seat just has no read.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import Callable

from .registry import Seat

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-opus-5"
MAX_LINES = 3
# Server-side refusal fallback (routes by refusal category). Only for models that support it.
_FALLBACK_MODELS = {"claude-opus-5", "claude-fable-5-1"}
_FALLBACK_BETA = "server-side-fallback-2026-07-01"

_NUMBER = re.compile(r"(?<![\w.])-?\d[\d,]*(?:\.\d+)?")

SYSTEM = (
    "You are the analyst for one AI executive seat. You receive that seat's owned outcome, "
    "its one number, its alarm, and a small JSON snapshot. Write at most 3 short lines, one "
    "insight per line, plain text, no bullets, no markdown. Say what the number means for "
    "the outcome and what a human should look at next. Use only numbers that appear in the "
    "input; never estimate, extrapolate or invent a figure. Do not recommend actions that "
    "send, spend, deploy or change anything; a human decides."
)


def _canon(token: str) -> float | None:
    try:
        return round(float(token.replace(",", "")), 4)
    except ValueError:
        return None


def allowed_numbers(seat: Seat, snap: dict) -> set:
    """Every number the model is allowed to say, in a few harmless renderings."""
    allowed = set()

    def add(v):
        if isinstance(v, bool):
            return
        if isinstance(v, (int, float)):
            for r in (v, round(v), round(v, 1), round(v, 2)):
                allowed.add(round(float(r), 4))
        elif isinstance(v, str):
            for tok in _NUMBER.findall(v):
                c = _canon(tok)
                if c is not None:
                    allowed.add(c)
        elif isinstance(v, dict):
            for x in v.values():
                add(x)
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)

    add(snap)
    if seat.alarm is not None:
        add(seat.alarm.value)
    return allowed


def grounded(lines: list[str], seat: Seat, snap: dict) -> list[str]:
    """Keep only lines whose every number is in the snapshot. Anything else is dropped."""
    ok = allowed_numbers(seat, snap)
    kept = []
    for line in lines:
        numbers = [_canon(t) for t in _NUMBER.findall(line)]
        if all(n is not None and n in ok for n in numbers):
            kept.append(line)
        else:
            logger.info("narrate: dropped an ungrounded line for %s", seat.role_id)
    return kept[:MAX_LINES]


def _prompt(seat: Seat, snap: dict) -> str:
    return json.dumps({
        "seat": seat.title, "owned_outcome": seat.owned_outcome, "number": seat.number,
        "unit": seat.unit.strip(), "better": seat.better,
        "alarm": str(seat.alarm) if seat.alarm else None, "snapshot": snap,
    }, sort_keys=True, default=str)


def make_narrator(model: str | None = None, client=None) -> Callable[[Seat, dict], list[str]] | None:
    """Return a narrator for the engine, or None when narration is off or unavailable."""
    if client is None:
        if os.environ.get("EXEC_CLAUDE_NARRATE", "").strip().lower() not in {"1", "true", "yes", "on"}:
            return None
        try:
            import anthropic
        except ImportError:
            logger.warning("EXEC_CLAUDE_NARRATE is on but `anthropic` is not installed")
            return None
        client = anthropic.Anthropic(timeout=60.0, max_retries=2)
    model = model or os.environ.get("EXEC_CLAUDE_MODEL", DEFAULT_MODEL)

    def narrate(seat: Seat, snap: dict) -> list[str]:
        kwargs = dict(model=model, max_tokens=16000, system=SYSTEM,
                      output_config={"effort": "low"},
                      messages=[{"role": "user", "content": _prompt(seat, snap)}])
        try:
            if model in _FALLBACK_MODELS:
                resp = client.beta.messages.create(betas=[_FALLBACK_BETA], fallbacks="default", **kwargs)
            else:
                resp = client.messages.create(**kwargs)
        except Exception as exc:  # never let the model break the brief
            logger.warning("narrate: %s for %s: %s", type(exc).__name__, seat.role_id, exc)
            return []
        if getattr(resp, "stop_reason", None) == "refusal":
            return []
        text = "\n".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        lines = [ln.strip(" -*\t") for ln in text.splitlines() if ln.strip()]
        return grounded(lines, seat, snap)

    return narrate
