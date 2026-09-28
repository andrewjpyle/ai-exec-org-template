"""CLI: python -m exec_org {seats|brief|deadman}"""

from __future__ import annotations

import sys

from . import roles  # noqa: F401  (registers the seats)
from .deadman import alert, check_brief_stalled, check_unarmed
from .engine import run_daily_brief
from .registry import Registry, is_armed


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "seats"
    if cmd == "seats":
        for s in Registry.all():
            state = "ARMED  " if is_armed(s) else "dormant"
            print(f"{state}  {s.title:<20} owns: {s.owned_outcome}  | number: {s.number}  | flag: {s.arm_flag}")
        return 0
    if cmd == "brief":
        print(run_daily_brief())
        return 0
    if cmd == "deadman":
        fired = [m for m in (check_brief_stalled(), check_unarmed()) if m]
        for m in fired:
            alert(m)
        return 1 if fired else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
