# An AI executive team that cannot act

A small, dependency-free template for running AI "executive seats" (CEO, CFO, CRO, CMO, CPO, COO, Chief of Staff) the safe way:

- **Seats declared in code.** The whole org chart is one file, `exec_org/roles.py`.
- **One daily engine, not seven.** A single job loops every armed seat and writes one brief.
- **Drafts only.** The engine has no code path that sends, spends, merges or changes anything. A human reads the brief and decides.
- **Armed one seat at a time.** Every seat ships dormant, and each has its own switch.
- **Two dead-man alarms** on a separate schedule and a separate channel: one fires if the brief stops landing, the other if seats get built but never switched on.

This is a trimmed-down version of the pattern running inside my own command center. There, seven seats read the systems that already hold the numbers (portfolio analytics, finance, CI, the agent session log) and a draft brief lands every afternoon. On 2026-09-27 the brief did not land. The stall dead-man, which only watches the engine, fired that afternoon. That is the reason both alarms are in here.

## The rule worth stealing

**Give every AI exec one owned outcome and one number. Not a job description.**

"Owns cash runway, measured in days" beats "helps with finance." The registry refuses a seat without a number:

```python
Seat("cfo", "AI CFO",
     owned_outcome="Cash, debt payoff and cost control",
     number="cash_runway_days",
     reads=["accounting export", "cloud bills"],
     snapshot=read_number("cash_runway_days"))
```

If a seat cannot name the number it moves, it is not a seat yet.

## Run it in two minutes

```bash
git clone <this repo> && cd ai_exec_org_template
cp examples/metrics.example.json metrics.json

python -m exec_org seats                        # all 7 seats, all dormant

EXEC_CFO_ENABLED=1 EXEC_METRICS_FILE=metrics.json python -m exec_org brief
cat briefs/brief_*.md                           # one DRAFT, one seat

python -m exec_org deadman                      # quiet: a brief just landed
```

Arm more seats with `EXEC_<ROLE>_ENABLED=1` (for example `EXEC_COO_ENABLED=1`), one at a time. Read a week of briefs from a seat before you arm the next.

## Make it yours

1. **Edit `exec_org/roles.py`.** Keep the seats you need and delete the rest. Rewrite each `owned_outcome` and `number` for your business.
2. **Replace the snapshot readers.** The examples read a JSON file so the template runs anywhere. Point each one at the system that already holds the number, **read-only**: your analytics API, an accounting export, CI, a database view.
3. **Never fabricate.** If a reader can't get the number, return `{"unavailable": "why"}`. The brief will say so instead of guessing. `safe_snapshot` also turns a crashing reader into an honest "unavailable".
4. **Pick where briefs land.** `FileSink` writes markdown files. Implement `write()` and `latest_written_at()` to send drafts to a doc, a ticket or an inbox instead. Keep it somewhere a human reads, not somewhere that acts.
5. **Schedule the brief and the dead-man separately.** See `examples/crontab.txt`. An alarm that shares a scheduler or queue with the thing it watches goes down with it. Set `EXEC_ALERT_WEBHOOK` to send alerts to Slack or similar, and `EXEC_ARM_BY=YYYY-MM-DD` to get nudged about seats you built but never armed.

## Adding an LLM

The engine deliberately writes numbers, not prose. If you want each seat to add a short analysis, have the model read the snapshot and write into the draft. Do not give it tools that act. Keep that boundary in code, not in a prompt.

## Tests

```bash
pip install pytest && pytest -q
```

The tests cover:
- Seven seats, each with one outcome and one number.
- Seats ship dormant and arm one at a time.
- The engine goes quiet when nothing is armed.
- Missing numbers show up as "unavailable", never invented.
- The stall dead-man stays quiet when a brief is fresh and fires when it's stale.
- The unarmed dead-man fires only after its deadline.

## License

MIT. By [Andrew Pyle](https://andrewjpyle.com): one operator, a fleet of Claude Code agents.
