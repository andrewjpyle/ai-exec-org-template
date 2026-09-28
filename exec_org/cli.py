"""exec-org: the command line.

    exec-org seats                 list the roster and which seats are armed
    exec-org brief [--dry-run]     compose today's draft brief (and write it to the sink)
    exec-org deadman               run both dead-man checks; exit 1 and alert if one fires
    exec-org init [DIR]            scaffold exec_roles.py, metrics.json, workflows, CLAUDE.md
    exec-org interview             8 questions (or --from company.md) -> a first roster
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def _load(args):
    from .loader import load_roles

    return load_roles(getattr(args, "roles", None))


def cmd_seats(args) -> int:
    from .registry import Registry, is_armed

    _load(args)
    for s in Registry.all():
        state = "ARMED  " if is_armed(s) else "dormant"
        alarm = f"alarm {s.alarm}{s.unit}" if s.alarm else "no alarm"
        print(f"{state}  {s.title:<20} {s.number:<30} {alarm:<22} {s.arm_flag}")
    return 0


def cmd_brief(args) -> int:
    from .engine import compose_brief, run_daily_brief
    from .narrate import make_narrator
    from .sinks import from_env

    module = _load(args)
    precedence = getattr(module, "PRECEDENCE", None)
    narrator = make_narrator()
    if args.dry_run:
        body = compose_brief(narrator=narrator, precedence=precedence)
        print(body if body else "No seats armed. Arm one: EXEC_CFO_ENABLED=1 (or EXEC_ARMED=cfo).")
        return 0
    result = run_daily_brief(sink=from_env(args.sink), narrator=narrator, precedence=precedence)
    print(result)
    return 0


def cmd_deadman(args) -> int:
    from .deadman import alert, check_brief_stalled, check_unarmed
    from .sinks import from_env

    _load(args)
    fired = [m for m in (check_brief_stalled(sink=from_env(args.sink)), check_unarmed()) if m]
    for m in fired:
        print(f"{alert(m)}: {m}")
    if not fired:
        print("dead-man: quiet (brief fresh, or nothing armed; no unarmed-seat deadline passed)")
    return 1 if fired else 0


def cmd_init(args) -> int:
    from .scaffold import scaffold

    written, skipped = scaffold(Path(args.dir), with_actions=not args.no_actions, force=args.force)
    for p in written:
        print(f"  wrote   {p}")
    for p in skipped:
        print(f"  kept    {p} (exists; use --force to overwrite)")
    print("\nNext: exec-org seats, then EXEC_ARMED=cfo exec-org brief --dry-run")
    return 0


def cmd_interview(args) -> int:
    from . import interview as iv

    if args.from_file:
        text = Path(args.from_file).read_text(encoding="utf-8")
        answers = iv.from_text(text)
    else:
        text = ""
        answers = iv.ask()
    seats = iv.roster(answers)
    if args.claude:
        seats = iv.polish_with_claude(seats, text or repr(answers))
    code = iv.render(seats)
    if not args.write:
        print(code)
        print(f"# {len(seats)} seats for a {answers.business} business. Re-run with --write to save exec_roles.py.")
        return 0
    for name, body in (("exec_roles.py", code), ("metrics.json", iv.metrics_stub(seats))):
        target = Path(name)
        if target.exists() and not args.force:
            print(f"  kept    {target} (exists; use --force to overwrite)")
            continue
        target.write_text(body, encoding="utf-8")
        print(f"  wrote   {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="exec-org", description="An AI executive team that cannot act.")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="cmd")

    def roles_arg(sp):
        sp.add_argument("--roles", help="path to a roles module (default: ./exec_roles.py, else the example)")

    sp = sub.add_parser("seats", help="list the roster")
    roles_arg(sp)
    sp.set_defaults(fn=cmd_seats)

    sp = sub.add_parser("brief", help="compose today's draft brief")
    roles_arg(sp)
    sp.add_argument("--sink", help="file (default), github, slack, or a comma list")
    sp.add_argument("--dry-run", action="store_true", help="print the brief; write nothing")
    sp.set_defaults(fn=cmd_brief)

    sp = sub.add_parser("deadman", help="run both dead-man checks")
    roles_arg(sp)
    sp.add_argument("--sink", help="where briefs land (to check freshness)")
    sp.set_defaults(fn=cmd_deadman)

    sp = sub.add_parser("init", help="scaffold a roster, workflows and CLAUDE.md into a repo")
    sp.add_argument("dir", nargs="?", default=".")
    sp.add_argument("--no-actions", action="store_true", help="skip the GitHub Actions workflows")
    sp.add_argument("--force", action="store_true", help="overwrite existing files")
    sp.set_defaults(fn=cmd_init)

    sp = sub.add_parser("interview", help="answer 8 questions (or --from company.md) to get a roster")
    sp.add_argument("--from", dest="from_file", help="read a company description instead of asking")
    sp.add_argument("--claude", action="store_true", help="let Claude polish outcome and fix wording")
    sp.add_argument("--write", action="store_true", help="write exec_roles.py and metrics.json")
    sp.add_argument("--force", action="store_true", help="overwrite existing files")
    sp.set_defaults(fn=cmd_interview)

    args = p.parse_args(argv)
    if not getattr(args, "fn", None):
        p.print_help()
        return 2
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
