# Contributing

Good contributions make it faster to go from clone to a first real brief, without weakening the
safety model.

**Most wanted:** read-only readers for common systems (Search Console, Plausible, Linear,
PagerDuty, QuickBooks exports), new seat templates for `exec_org/catalog.py`, and sample rosters for
kinds of business we do not cover yet.

**Rules** (also in `CLAUDE.md`):
1. Core stays dependency-free. Optional integrations go behind an extra.
2. Readers are read-only, take tokens from env vars, and return `unavailable` instead of guessing.
3. Every new guard comes with a test that fails when the guard is removed.
4. `ruff check exec_org tests` and `pytest -q` pass.

Open an issue first for anything bigger than a reader or a seat template.
