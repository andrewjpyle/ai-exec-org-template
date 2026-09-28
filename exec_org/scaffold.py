"""`exec-org init`: drop a working exec org into any repo in one command.

Writes (never overwrites unless --force):
    exec_roles.py                          your roster (starts as the Acme example)
    metrics.json                           sample numbers so the first brief runs immediately
    CLAUDE.md                              how Claude Code should work on your roster
    .claude/skills/exec-seat/SKILL.md      a Claude Code skill: add or tune a seat correctly
    .github/workflows/exec-brief.yml       the daily brief (to a GitHub issue)
    .github/workflows/exec-deadman.yml     the dead-man, on its own schedule
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

FILES = [
    ("exec_roles.py", "exec_roles.py"),
    ("metrics.json", "metrics.json"),
    ("CLAUDE.md", "CLAUDE.md"),
    ("skills/exec-seat/SKILL.md", ".claude/skills/exec-seat/SKILL.md"),
]
ACTIONS = [
    ("workflows/exec-brief.yml", ".github/workflows/exec-brief.yml"),
    ("workflows/exec-deadman.yml", ".github/workflows/exec-deadman.yml"),
]


def _template(rel: str) -> str:
    return (resources.files("exec_org") / "templates" / rel).read_text(encoding="utf-8")


def scaffold(root: Path, with_actions: bool = True, force: bool = False) -> tuple[list[Path], list[Path]]:
    written, skipped = [], []
    for src, dst in FILES + (ACTIONS if with_actions else []):
        target = root / dst
        if target.exists() and not force:
            skipped.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_template(src), encoding="utf-8")
        written.append(target)
    return written, skipped
