"""Generic readers: a JSON file, any JSON HTTP endpoint, a SQL query, and "no feed yet".

Every factory returns a zero-argument snapshot function that returns ``{key: value}``.
Errors are allowed to raise: ``safe_snapshot`` turns them into an honest "unavailable".
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from collections.abc import Callable

from ._http import dig, get_json

Snapshot = Callable[[], dict]

_SELECT_ONLY = re.compile(r"^\s*(with|select)\b", re.IGNORECASE)
_WRITE_WORDS = re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|replace|attach|pragma)\b",
                          re.IGNORECASE)


def json_file(key: str, path: str | None = None) -> Snapshot:
    """Read one number from a JSON file (default: $EXEC_METRICS_FILE or ./metrics.json).

    A missing key or a null value reads as unavailable, never as 0.
    """

    def _snapshot() -> dict:
        p = path or os.environ.get("EXEC_METRICS_FILE", "metrics.json")
        try:
            with open(p, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            return {"unavailable": f"metrics file not found: {p}"}
        if data.get(key) is None:
            return {"unavailable": f"{key} not reported"}
        return {key: data[key]}

    return _snapshot


def http_json(key: str, url: str, path: str = "", token_env: str | None = None,
              header: str = "Authorization", scheme: str = "Bearer") -> Snapshot:
    """Read one number from any JSON API. `path` is a dotted path into the response.

    The token comes from an env var you name, never from code.
    """

    def _snapshot() -> dict:
        headers = {}
        if token_env:
            token = os.environ.get(token_env, "")
            if not token:
                return {"unavailable": f"{token_env} not set"}
            headers[header] = f"{scheme} {token}".strip()
        return {key: dig(get_json(url, headers=headers), path)}

    return _snapshot


def sql(key: str, query: str, sqlite_path: str | None = None,
        connect: Callable[[], object] | None = None) -> Snapshot:
    """Read one number with a SELECT. Works with sqlite out of the box, or any DB-API
    driver via `connect` (e.g. ``lambda: psycopg.connect(os.environ["DB_URL"])``).

    Refuses anything that is not a single read-only SELECT. Use a read-only DB user too.
    """
    if not _SELECT_ONLY.match(query) or _WRITE_WORDS.search(query) or ";" in query.strip().rstrip(";"):
        raise ValueError("exec_org.readers.sql only runs a single read-only SELECT")

    def _snapshot() -> dict:
        if connect is not None:
            conn = connect()
        else:
            p = sqlite_path or os.environ.get("EXEC_SQLITE_PATH", "")
            if not p:
                return {"unavailable": "no database configured"}
            conn = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
        try:
            cur = conn.cursor()
            cur.execute(query)
            row = cur.fetchone()
        finally:
            conn.close()
        if not row or row[0] is None:
            return {"unavailable": f"{key}: query returned no value"}
        return {key: row[0]}

    return _snapshot


def no_feed(key: str, what: str) -> Snapshot:
    """Declare an honest gap. The brief says "not measured" instead of printing a 0.

    Use it for numbers you know matter but cannot read yet (dependency vulns, leak scans).
    """

    def _snapshot() -> dict:
        return {"unavailable": f"no_feed: {what}"}

    return _snapshot
