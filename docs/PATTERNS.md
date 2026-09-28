# The eight patterns

Each pattern names the failure it prevents and where the code enforces it. Borrow them even if
you never run this repo.

## 1. One outcome, one number
**Prevents:** seats that produce essays and move nothing.
A seat owns one outcome and one number that measures it. "Owns cash runway, in days" is a seat.
"Helps with finance" is not.
**In code:** `Registry.register` refuses a seat without an `owned_outcome` and a `number`
(`exec_org/registry.py`).

## 2. Drafts only
**Prevents:** an agent that is confidently wrong in production.
The engine composes a brief and hands it to a sink that a person reads. There is no code path that
sends, spends, merges or deploys. Readers are GET and SELECT only.
**In code:** `exec_org/readers/_http.py` only does GET; `readers.sql` refuses anything but a single
`SELECT`; sinks write to files, issues or Slack.

## 3. Declared in code
**Prevents:** an org chart silently changed by a data migration or an admin panel.
The roster is a Python file under version control. Changing a seat is a reviewed diff.
**In code:** `exec_roles.py`, loaded by `exec_org/loader.py`.

## 4. Arm one seat at a time
**Prevents:** nine new seats, nine new failure modes, all at once.
Every seat ships dormant. It runs only when its own switch is on (`EXEC_CFO_ENABLED=1`, or
`EXEC_ARMED=cfo`). Nothing arms every seat at once. Read a week of one seat's briefs before
trusting the next.
**In code:** `is_armed` in `exec_org/registry.py`.

## 5. Unavailable, never 0
**Prevents:** a missing feed that reads as "all clear".
A reader that cannot get its number returns `{"unavailable": "why"}`. A reader that crashes is
caught and reported the same way. A number that matters but has no source yet uses `no_feed`,
which prints "not measured".
**In code:** `safe_snapshot` in `registry.py`, `readers.no_feed`, and the engine's rendering of
unavailable seats.

## 6. Blind inputs block an all-clear
**Prevents:** "nothing fired" when half the seats were unreadable.
Today's one action goes to the first seat, in precedence order, whose alarm fires on a *readable*
number. If none fired but some were blind, the brief says to restore the blind seats first.
**In code:** `one_action` in `exec_org/arbitration.py`.

## 7. Dead-man on its own channel
**Prevents:** the alarm dying with the thing it watches.
The dead-man is a separate job on a separate schedule, and it alerts on a separate channel (an
`exec-alert` issue or a webhook), never through the brief's sink. If it cannot even read the sink,
it treats that as a stall.
**In code:** `check_brief_stalled` and `alert` in `exec_org/deadman.py`; the two workflows in
`exec_org/templates/workflows/`.

## 8. Built but never armed is a failure
**Prevents:** seats that exist in code and in nobody's day.
Set `EXEC_ARM_BY=YYYY-MM-DD`. After that date the second dead-man names every seat that is still
dormant.
**In code:** `check_unarmed` in `exec_org/deadman.py`.

## And one for the optional Claude layer: grounded numbers
**Prevents:** a fluent paragraph with an invented figure in it.
Claude gets no tools. Every number in its lines must appear in the seat's snapshot or alarm, or
the line is dropped. The brief's numbers, deltas and fix-first never depend on the model.
**In code:** `grounded` in `exec_org/narrate.py`.
