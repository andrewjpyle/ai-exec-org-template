"""The seat registry: every AI executive declared in code, in one place.

A seat is not a job description. It is one owned outcome, one number that measures
it, a read-only snapshot of where that number stands today, and (optionally) the
threshold at which that number becomes the thing to fix first.

Rules baked in:
  * The roster lives in code, not a database, so it is reviewed, versioned and never
    silently changed by a data migration.
  * Every seat ships DORMANT. It is armed on its own, with its own env flag, so one
    seat can prove itself before the next one is trusted.
  * A snapshot never raises and never invents a value. If it cannot read the number
    it says so ("unavailable") instead of guessing.
"""

from __future__ import annotations

import logging
import operator
import os
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on"}
_OPS = {">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt}


@dataclass(frozen=True)
class Threshold:
    """When the seat's number crosses this line, the seat's `fix` becomes its fix-first.

    `Threshold(">=", 15)` on a change-failure rate means "15% or worse is a problem".
    """

    op: str
    value: float

    def __post_init__(self):
        if self.op not in _OPS:
            raise ValueError(f"threshold op must be one of {sorted(_OPS)}, got {self.op!r}")

    def crossed(self, number) -> bool:
        try:
            return _OPS[self.op](float(number), float(self.value))
        except (TypeError, ValueError):
            return False

    def __str__(self) -> str:
        v = int(self.value) if float(self.value).is_integer() else self.value
        return f"{self.op} {v}"


@dataclass
class Seat:
    """One AI executive seat."""

    role_id: str                  # short slug, e.g. "cfo"
    title: str                    # display title, e.g. "AI CFO"
    owned_outcome: str            # the ONE outcome this seat owns
    number: str                   # the ONE number that measures it (a key in the snapshot)
    snapshot: Callable[[], dict] | None = None   # read-only, returns a dict
    unit: str = ""                # printed after the number, e.g. "%", " days", " USD/day"
    better: str = "up"            # "up" or "down": which direction is good (drives delta arrows)
    alarm: Threshold | None = None   # when crossed, `fix` becomes this seat's fix-first
    fix: str = ""                 # the one action to take when the alarm fires
    reads: list[str] = field(default_factory=list)  # existing systems it reads (docs only)

    def __post_init__(self):
        if self.better not in ("up", "down"):
            raise ValueError(f"seat {self.role_id!r}: better must be 'up' or 'down'")
        if self.alarm is not None and not self.fix:
            raise ValueError(f"seat {self.role_id!r}: an alarm needs a `fix` action")

    @property
    def arm_flag(self) -> str:
        return f"EXEC_{self.role_id.upper()}_ENABLED"


class Registry:
    """In-memory registry of seats, populated by a roles module at import time."""

    _seats: dict[str, Seat] = {}

    @classmethod
    def register(cls, seat: Seat) -> Seat:
        if not seat.owned_outcome or not seat.number:
            raise ValueError(
                f"seat {seat.role_id!r} needs one owned outcome and one number"
            )
        cls._seats[seat.role_id] = seat
        return seat

    @classmethod
    def get(cls, role_id: str) -> Seat | None:
        return cls._seats.get(role_id)

    @classmethod
    def all(cls) -> list[Seat]:
        return list(cls._seats.values())

    @classmethod
    def clear(cls) -> None:
        cls._seats.clear()


def is_armed(seat: Seat, env: dict | None = None) -> bool:
    """A seat is armed only when ITS OWN switch is on: `EXEC_<ROLE>_ENABLED=1`, or its role id
    listed in `EXEC_ARMED` (a comma list, handy in CI: `EXEC_ARMED=cfo,cto`). Nothing arms
    every seat at once; you name each one."""
    env = os.environ if env is None else env
    if env.get(seat.arm_flag, "").strip().lower() in _TRUTHY:
        return True
    listed = {r.strip().lower() for r in env.get("EXEC_ARMED", "").split(",") if r.strip()}
    return seat.role_id in listed


def armed_seats(env: dict | None = None) -> list[Seat]:
    return [s for s in Registry.all() if is_armed(s, env)]


def safe_snapshot(seat: Seat) -> dict:
    """Run a seat's snapshot defensively. Never raises, never fabricates."""
    if seat.snapshot is None:
        return {"unavailable": "no snapshot wired yet"}
    try:
        snap = seat.snapshot()
    except Exception as exc:  # a broken reader must not take the brief down
        logger.warning("snapshot for %s failed: %s", seat.role_id, exc)
        return {"unavailable": f"snapshot error: {type(exc).__name__}: {str(exc)[:120]}"}
    if not snap:
        return {"unavailable": "snapshot returned nothing"}
    if "unavailable" not in snap and snap.get(seat.number) is None:
        return {"unavailable": f"{seat.number} not reported", **snap}
    return snap


def headline(seat: Seat, snap: dict):
    """The seat's number from its snapshot, or None when unreadable."""
    if "unavailable" in snap:
        return None
    return snap.get(seat.number)


def fix_first(seat: Seat, snap: dict) -> str | None:
    """The seat's one action when its alarm fires on a readable number, else None."""
    value = headline(seat, snap)
    if seat.alarm is None or value is None or not seat.alarm.crossed(value):
        return None
    return f"{seat.fix} ({seat.number} = {value}{seat.unit}, alarm {seat.alarm}{seat.unit})"
