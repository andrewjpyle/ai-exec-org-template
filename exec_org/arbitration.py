"""The CEO's job, made deterministic: pick TODAY'S ONE ACTION across all armed seats.

Seats are checked in a strict precedence order declared in code (edit PRECEDENCE in your
roles module to change it). The first seat whose alarm fires on a READABLE number wins,
and its fix becomes the day's one action.

An unreadable seat is BLIND, not "fine". If nothing fired but some seats were blind, the
brief says so instead of reporting an all-clear. An all-clear over blind inputs is not an
all-clear.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .registry import Seat, fix_first, headline

# Existential first (cash, security, uptime), then quality, then growth, then the fleet.
PRECEDENCE: tuple[str, ...] = ("cfo", "ciso", "coo", "cto", "cro", "cmo", "cpo", "chief_of_staff", "ceo")


@dataclass
class Decision:
    action: str
    owner: str | None
    why: str
    blind: list[str] = field(default_factory=list)


def one_action(readings: Sequence[tuple[Seat, dict]],
               precedence: Sequence[str] | None = None) -> Decision:
    order = list(precedence or PRECEDENCE)
    by_role = {seat.role_id: (seat, snap) for seat, snap in readings}
    ranked = [r for r in order if r in by_role] + [r for r in by_role if r not in order]

    blind: list[str] = []
    for position, role in enumerate(ranked, start=1):
        seat, snap = by_role[role]
        if headline(seat, snap) is None:
            blind.append(seat.title)
            continue
        line = fix_first(seat, snap)
        if line:
            return Decision(action=line, owner=seat.title,
                            why=f"{seat.title} is #{position} in precedence and its alarm fired",
                            blind=blind)
    if blind:
        return Decision(action="No alarm fired on the readable seats. Restore the blind ones before "
                               "treating today as clear: " + ", ".join(blind),
                        owner=None, why="an all-clear over blind inputs is not an all-clear", blind=blind)
    return Decision(action="Nothing is over threshold. Hold course; read the seats below.",
                    owner=None, why="every armed seat was readable and inside its threshold")
