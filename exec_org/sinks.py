"""Where a draft brief lands. The default is a folder of markdown files.

Swap in your own sink (a ticket, a doc, an inbox) by implementing write() and
latest_written_at(). Keep it a place a human READS, never a place that acts.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol


class BriefSink(Protocol):
    def write(self, body: str) -> str: ...
    def latest_written_at(self) -> Optional[datetime]: ...


class FileSink:
    """Writes briefs/brief_YYYY-MM-DD.md. Re-running the same day overwrites it."""

    def __init__(self, directory: Optional[str] = None):
        self.directory = Path(directory or os.environ.get("EXEC_BRIEF_DIR", "briefs"))

    def write(self, body: str) -> str:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self.directory / f"brief_{datetime.now(timezone.utc):%Y-%m-%d}.md"
        path.write_text(body, encoding="utf-8")
        return str(path)

    def latest_written_at(self) -> Optional[datetime]:
        files = list(self.directory.glob("brief_*.md")) if self.directory.exists() else []
        if not files:
            return None
        newest = max(f.stat().st_mtime for f in files)
        return datetime.fromtimestamp(newest, tz=timezone.utc)
