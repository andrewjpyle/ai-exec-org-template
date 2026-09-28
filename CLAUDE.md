# Working on ai-exec-org-template (for Claude Code and contributors)

This is the LIBRARY. For the rules Claude Code follows inside a user's own roster, see
`exec_org/templates/CLAUDE.md` (that is what `exec-org init` installs).

## Non-negotiables
- **Core stays stdlib-only.** New dependencies go behind an optional extra (like `[claude]`).
- **Drafts only.** Nothing in `exec_org/` may send, spend, merge, deploy or change an external
  system. Readers GET/SELECT only; sinks write only to places people read.
- **Never fabricate.** Unknown → `{"unavailable": "why"}`. Never 0, never a guess.
- **Every guard has a test that fails without it.** When you add a guard, break it on purpose and
  confirm a test goes red before you ship.
- **Copy voice:** no hashtags, no em dashes, plain words.

## Checks
```bash
pip install -e ".[dev]"
ruff check exec_org tests
pytest -q
cd "$(mktemp -d)" && exec-org init . && EXEC_ARMED=cfo,cto,ciso exec-org brief --dry-run
```

## Graphics
`docs/assets/src/build.py` generates the HTML; render each at 2x with a headless Chromium
(`--force-device-scale-factor=2 --window-size=1400,760 --screenshot=...`). Sample data only.
