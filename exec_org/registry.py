"""The seat registry: every AI executive declared in code, in one place.

A seat is not a job description. It is one owned outcome, one number that
measures it, and a read-only snapshot of where that number stands today.

Rules baked in:
  * The roster lives in code (roles.py), not a database, so it is reviewed,
    versioned and never silently changed by a data migration.
  * Every seat ships DORMANT. It is armed on its own, with its own env flag,
    so one seat can prove itself before the next one is trusted.
  * A snapshot never raises and never invents a value. If it cannot read the
    number it says so ("unavailable") instead of guessing.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

_TRUTHY = {"1", "true", "yes", "on"}


@dataclass
class Seat:
    """One AI executive seat."""

    role_id: str                 # short slug, e.g. "cfo"
    title: str                   # display title, e.g. "AI CFO"
    owned_outcome: str           # the ONE outcome this seat owns
    number: str                  # the ONE number that measures it
    reads: List[str] = field(default_factory=list)  # existing systems it reads
    snapshot: Optional[Callable[[], dict]] = None    # read-only, returns a dict

    @property
    def arm_flag(self) -> str:
        return f"EXEC_{self.role_id.upper()}_ENABLED"


class Registry:
    """In-memory registry of seats, populated by roles.py at import time."""

    _seats: Dict[str, Seat] = {}

    @classmethod
    def register(cls, seat: Seat) -> Seat:
        if not seat.owned_outcome or not seat.number:
            raise ValueError(
                f"seat {seat.role_id!r} needs one owned outcome and one number"
            )
        cls._seats[seat.role_id] = seat
        return seat

    @classmethod
    def get(cls, role_id: str) -> Optional[Seat]:
        return cls._seats.get(role_id)

    @classmethod
    def all(cls) -> List[Seat]:
        return list(cls._seats.values())

    @classmethod
    def clear(cls) -> None:
        cls._seats.clear()


def is_armed(seat: Seat, env: Optional[dict] = None) -> bool:
    """A seat is armed only when its own env flag is truthy."""
    env = os.environ if env is None else env
    return env.get(seat.arm_flag, "").strip().lower() in _TRUTHY


def armed_seats(env: Optional[dict] = None) -> List[Seat]:
    return [s for s in Registry.all() if is_armed(s, env)]


def safe_snapshot(seat: Seat) -> dict:
    """Run a seat's snapshot defensively. Never raises, never fabricates."""
    if seat.snapshot is None:
        return {"unavailable": "no snapshot wired yet"}
    try:
        return seat.snapshot() or {"unavailable": "snapshot returned nothing"}
    except Exception as exc:  # a broken reader must not take the brief down
        logger.warning("snapshot for %s failed: %s", seat.role_id, exc)
        return {"unavailable": f"snapshot error: {type(exc).__name__}"}
