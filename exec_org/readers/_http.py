"""A tiny stdlib HTTP helper shared by the connectors. GET only, JSON only, always a timeout.

Readers never POST, PUT or DELETE. That is the whole point of a seat: it reads.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

USER_AGENT = "ai-exec-org-template (+https://github.com/andrewjpyle/ai-exec-org-template)"
TIMEOUT_SECONDS = 20


def get_json(url: str, params: dict | None = None, headers: dict | None = None,
             timeout: float = TIMEOUT_SECONDS):
    if params:
        url = f"{url}{'&' if '?' in url else '?'}{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, method="GET", headers={
        "Accept": "application/json", "User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8") or "null")


def dig(data, path: str):
    """Follow a dotted path into JSON, e.g. "data.0.total". Raises KeyError if missing."""
    if not path:
        return data
    for part in path.split("."):
        if isinstance(data, list):
            data = data[int(part)]
        elif isinstance(data, dict):
            data = data[part]
        else:
            raise KeyError(path)
    return data
