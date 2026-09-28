"""The roster. Edit this file to define your own seats.

Each seat below is an EXAMPLE. The snapshot readers pull from a simple JSON
metrics file (see examples/metrics.example.json) so the template runs out of
the box. Replace each reader with a read-only query against the system that
already holds the number: your analytics, your accounting export, your CI.

Keep the rule: one owned outcome, one number. If you cannot name the number a
seat moves, it is not a seat yet.
"""

from __future__ import annotations

import json
import os
from typing import Callable

from .registry import Registry, Seat


def _metrics() -> dict:
    path = os.environ.get("EXEC_METRICS_FILE", "metrics.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def read_number(key: str) -> Callable[[], dict]:
    """Build a read-only snapshot that reports one number, or says it can't."""

    def _snapshot() -> dict:
        try:
            data = _metrics()
        except FileNotFoundError:
            return {"unavailable": "metrics file not found"}
        if key not in data or data[key] is None:
            return {"unavailable": f"{key} not reported"}
        return {key: data[key]}

    return _snapshot


SEATS = [
    Seat("ceo", "AI CEO",
         owned_outcome="The North Star metric",
         number="north_star",
         reads=["analytics warehouse", "initiative list"],
         snapshot=read_number("north_star")),
    Seat("cfo", "AI CFO",
         owned_outcome="Cash, debt payoff and cost control",
         number="cash_runway_days",
         reads=["accounting export", "cloud bills"],
         snapshot=read_number("cash_runway_days")),
    Seat("cro", "AI CRO",
         owned_outcome="Revenue per day",
         number="revenue_per_day",
         reads=["billing", "CRM"],
         snapshot=read_number("revenue_per_day")),
    Seat("cmo", "AI CMO",
         owned_outcome="Demand and content quality",
         number="weekly_organic_clicks",
         reads=["search console", "content calendar"],
         snapshot=read_number("weekly_organic_clicks")),
    Seat("cpo", "AI CPO",
         owned_outcome="Which products earn their place",
         number="products_flagged_for_review",
         reads=["product analytics"],
         snapshot=read_number("products_flagged_for_review")),
    Seat("coo", "AI COO",
         owned_outcome="Infra, CI, deploys and uptime",
         number="failed_deploys_7d",
         reads=["CI", "uptime monitor"],
         snapshot=read_number("failed_deploys_7d")),
    Seat("chief_of_staff", "AI Chief of Staff",
         owned_outcome="The agent fleet: who is running, what is stuck",
         number="stale_agent_sessions",
         reads=["agent session log"],
         snapshot=read_number("stale_agent_sessions")),
]

for _seat in SEATS:
    Registry.register(_seat)
