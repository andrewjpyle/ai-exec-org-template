# AI executive org: working rules for Claude Code

This repo runs an AI executive team that **cannot act**. Seats read numbers and write one
daily DRAFT brief that a human reads. Keep it that way.

## The rules (do not weaken these)
1. **One outcome, one number per seat.** A seat without a number is refused by the registry. If you
   can't name the number a seat moves, propose one and ask. Don't invent a vague seat.
2. **Readers are read-only.** Use `exec_org.readers` (GET-only HTTP, SELECT-only SQL). Never write
   a reader that POSTs, updates, sends, deploys or spends. Tokens are read-only and come from env vars.
3. **Never fabricate.** If a number can't be read, return `{"unavailable": "why"}` or use
   `readers.no_feed(...)`. Never return 0 for "unknown".
4. **Arm one seat at a time.** Seats ship dormant (`EXEC_<ROLE>_ENABLED`, or `EXEC_ARMED=cfo,cto`).
   Don't arm a new seat in the same change that adds it.
5. **Alarms need a fix.** `alarm=Threshold(...)` requires `fix="the one action"`. Keep fixes to one
   concrete action a human can take today.
6. **Drafts only.** Sinks are places people read (files, issues, Slack). Nothing acts on the brief.

## Where things live
- `exec_roles.py`: the roster (the only file most changes touch)
- `metrics.json`: sample numbers until each seat has a real reader
- `.github/workflows/exec-brief.yml` and `exec-deadman.yml`: separate schedules, on purpose

## Checking your work
```bash
exec-org seats                               # the roster parses, flags are unique
EXEC_ARMED=<role> exec-org brief --dry-run   # the new seat renders a real number (or honest unavailable)
```

Use the `exec-seat` skill (`.claude/skills/exec-seat/SKILL.md`) to add or tune a seat.
