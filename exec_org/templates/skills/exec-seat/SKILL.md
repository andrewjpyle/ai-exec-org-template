---
name: exec-seat
description: Add, tune, or wire an AI executive seat in exec_roles.py. Use when the user says "add a CFO seat", "give the CTO a real number", "wire the CRO to Stripe", "what seats do I need", or wants to change a seat's alarm or fix. Enforces one outcome + one number, read-only readers, honest unavailable, dormant on ship.
---

# exec-seat: add or tune a seat the right way

A seat is **one owned outcome, one number, one alarm, one fix**. Your job is to get those four
right for THIS business, wire a read-only reader, and prove it renders. Never arm it.

## 1. Pin the outcome and the number
- Ask what the seat owns in plain words ("customers who stay"), then the ONE number that moves
  when that outcome improves or slips ("monthly_churn_pct"). Snake_case, units in `unit`.
- If they're unsure, check the catalog for a starting point: `python -c "from exec_org.catalog import CATALOG; print(sorted(CATALOG))"`,
  or run `exec-org interview --from company.md` for a whole first roster.
- Set `better="up"` or `"down"`. It drives the ▲/▼ "better/worse" deltas.

## 2. Set the alarm and the fix
- `alarm=Threshold(op, value)`: the line where this number becomes the day's problem.
  Start conservative; say it's a starting value to ratchet.
- `fix="..."`: ONE concrete action a human can take today. Not "improve X". Something like "Call every
  account that churned this month".

## 3. Wire a read-only reader
Prefer, in order:
1. `readers.github.change_failure_rate("org/repo")` or `ci_pass_rate(...)` for engineering seats
2. `readers.stripe.revenue_per_day(...)` for revenue (RESTRICTED read-only key only, `rk_...`)
3. `readers.sql("key", "SELECT ...", connect=...)` against a read-only DB user or a view
4. `readers.http_json("key", url, path="data.total", token_env="X_TOKEN")` for any JSON API
5. `readers.json_file("key")` while there is no feed yet
6. `readers.no_feed("key", "why")` when the number matters but can't be read yet. It shows as
   "not measured", never as 0.

Never write a reader that POSTs, updates or sends. Tokens come from env vars, never from code.

## 4. Prove it
```bash
exec-org seats
EXEC_ARMED=<role_id> exec-org brief --dry-run
```
The seat must show a real number, or an honest `unavailable (...)` saying why. Show the user the
rendered section. **Do not arm the seat** (no `EXEC_ARMED` in workflow vars, no `EXEC_<ROLE>_ENABLED`
in env). Arming is the human's call, one seat at a time.

## 5. Precedence
If the seat's alarm should outrank others in "Today's one action", add its role_id to `PRECEDENCE`
in the right place. Existential first (cash, security, uptime), then quality, then growth.
