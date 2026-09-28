"""Read-only connectors. Each factory returns a snapshot function for a Seat.

    from exec_org.readers import json_file, http_json, sql, no_feed, github, stripe

    Seat("cto", "AI CTO", owned_outcome="...", number="change_failure_rate_pct",
         snapshot=github.change_failure_rate("acme/web"))
"""

from . import github, stripe
from .basic import http_json, json_file, no_feed, sql

__all__ = ["json_file", "http_json", "sql", "no_feed", "github", "stripe"]
