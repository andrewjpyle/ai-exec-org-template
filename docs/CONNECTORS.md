# Connectors (readers)

Every reader is a factory that returns a zero-argument snapshot function for a `Seat`. They are
read-only by construction: HTTP readers only GET, the SQL reader only runs one `SELECT`, and
tokens always come from environment variables.

If a reader raises, `safe_snapshot` catches it and the brief shows `unavailable (snapshot error ...)`.
It never shows a made-up number.

## `json_file(key, path=None)`
Reads one number from a JSON file. The default path is `$EXEC_METRICS_FILE`, then `./metrics.json`.
A missing key or a `null` reads as unavailable.
Good for: getting started, and numbers another job already exports.

## `http_json(key, url, path="", token_env=None, header="Authorization", scheme="Bearer")`
Reads one number from any JSON API. `path` is a dotted path into the response (`data.0.total`).
```python
http_json("weekly_qualified_leads", "https://api.example-crm.com/v1/stats",
          path="leads.qualified_7d", token_env="CRM_TOKEN")
```

## `sql(key, query, sqlite_path=None, connect=None)`
Reads the first column of the first row of a single `SELECT` (or `WITH ... SELECT`). Write
keywords and multiple statements are refused when the seat is defined, not when it runs.
```python
import os, psycopg
sql("cash_runway_days", "SELECT runway_days FROM finance_summary",
    connect=lambda: psycopg.connect(os.environ["READONLY_DB_URL"]))
```
Use a read-only database user as well. The keyword guard is a seatbelt, not a permission system.

## `github.change_failure_rate(repo, environment="production", days=30)`
From the GitHub Deployments API: (failed + errored) / finished deployments, in percent, using each
deployment's latest status. Pending and in-progress deployments are not counted.
Token: `$GITHUB_TOKEN`, read-only (Deployments: read). In Actions: `permissions: {deployments: read}`.

## `github.ci_pass_rate(repo, branch="main", days=7)`
Share of completed GitHub Actions runs on `branch` that succeeded (cancelled runs are ignored).
Token: `$GITHUB_TOKEN` (Actions: read).

## `stripe.revenue_per_day(days=7, currency="usd")`
Charges plus payments minus refunds from balance transactions, averaged per day. Paginates.
Key: `$STRIPE_API_KEY`, which must be a **restricted** key (`rk_...`) with read access to Balance
only. A secret key (`sk_...`) is refused, because a seat should never hold a key that can create
charges or refunds.

## `no_feed(key, what)`
An honest gap. The seat shows `unavailable (no_feed: ...)` so nobody mistakes "not measured"
for "zero". Swap it for a real reader when one exists.

## Writing your own
Any function that returns `{number_key: value}` (plus optional extra keys, which the brief lists)
or `{"unavailable": "why"}` works:
```python
def open_incidents():
    data = my_pagerduty_client.list(status="triggered")   # read-only call
    return {"open_incidents": len(data)}
```
Rules: read-only, token from env, no retries that hide failures, and never return 0 for "unknown".
