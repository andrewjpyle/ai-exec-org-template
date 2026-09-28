# Changelog

## 0.2.0 (2026-09-28)
- **Nine seats**: adds AI CTO (change-failure rate) and AI CISO (open critical findings).
- **Alarms and fix-first**: `Threshold` on each seat, with one concrete fix when it fires.
- **Today's one action**: CEO arbitration over all armed seats in a declared precedence order;
  blind (unreadable) seats block an all-clear.
- **Day-over-day deltas** via an invisible metrics marker, aware of which direction is good.
- **Read-only connectors**: `json_file`, `http_json`, `sql` (SELECT-only), `github`
  (change-failure rate, CI pass rate), `stripe` (revenue per day, restricted keys only), `no_feed`.
- **Sinks**: file, GitHub issue, Slack, multi. The dead-man alerts on a separate channel.
- **CLI**: `exec-org seats | brief [--dry-run] | deadman | init | interview`.
- **Interview**: 8 questions or `--from company.md` produce a roster from a 12-seat catalog.
- **Optional Claude layer**: advisory read per seat, no tools, numbers grounded against the snapshot.
- **Claude Code**: `CLAUDE.md` and the `exec-seat` skill, installed by `exec-org init`.
- **GitHub Actions**: daily brief and dead-man workflows; CI on Python 3.10 to 3.13; a live demo
  whose CTO seat reads this repo's real CI pass rate.

## 0.1.0 (2026-09-28)
- First release: seven seats in code, one daily engine writing drafts, two dead-man alarms.
