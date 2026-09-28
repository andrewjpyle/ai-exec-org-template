# Running the brief on GitHub Actions

`exec-org init` writes two workflows into `.github/workflows/`. They are separate on purpose.

## `exec-brief.yml`: the daily draft
- Runs daily at 13:30 UTC (edit the cron to a time you actually read it) and on manual dispatch.
- Files the brief as an issue labeled `exec-brief`. Deltas come from the previous `exec-brief` issue.
- Token permissions: `contents: read`, `issues: write`, `deployments: read`, `actions: read`.
  It cannot push, merge or deploy.

## `exec-deadman.yml`: the watcher
- Runs about 2.5 hours after the brief, as its own job.
- If seats are armed and no `exec-brief` issue appeared in 26 hours, it opens an `exec-alert`
  issue (or posts to `EXEC_ALERT_WEBHOOK`) and fails the job, so GitHub's own failure email fires too.
- If `EXEC_ARM_BY` is set and seats are still dormant after that date, it names them.

## Arming seats
Settings > Secrets and variables > Actions > **Variables**:

| Variable | Example | Meaning |
|---|---|---|
| `EXEC_ARMED` | `cfo` then `cfo,cto` | which seats run, one at a time |
| `EXEC_ARM_BY` | `2026-10-15` | optional: nudge about seats still dormant after this date |
| `EXEC_CLAUDE_NARRATE` | `1` | optional: Claude's advisory read (needs the secret below) |

**Secrets**, only for the readers you use: `STRIPE_API_KEY` (restricted `rk_` key),
`ANTHROPIC_API_KEY`, `EXEC_ALERT_WEBHOOK`.

## Reading GitHub data from the same workflow
`readers.github.change_failure_rate("your-org/your-repo")` and `ci_pass_rate(...)` work with the
job's built-in `GITHUB_TOKEN`, thanks to the `deployments: read` and `actions: read` permissions.

## Not on GitHub?
The same two commands work anywhere with a scheduler. Keep them as two separate jobs:
```cron
30 13 * * *  cd /srv/exec-org && exec-org brief
10 16 * * *  cd /srv/exec-org && EXEC_ALERT_WEBHOOK=https://hooks.example.com/x exec-org deadman
```
