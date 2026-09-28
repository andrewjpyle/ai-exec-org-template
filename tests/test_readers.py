import sqlite3
from datetime import datetime, timezone

import pytest
from conftest import FakeHTTP

from exec_org.readers import basic, github, json_file, no_feed, sql, stripe

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)


def test_json_file_reads_a_number_and_null_is_unavailable(set_metrics):
    assert json_file("cash_runway_days")() == {"cash_runway_days": 140}
    set_metrics(cash_runway_days=None)
    assert "unavailable" in json_file("cash_runway_days")()
    assert json_file("x", path="/nope.json")()["unavailable"].startswith("metrics file not found")


def test_no_feed_is_an_honest_gap():
    assert no_feed("dependency_vulns", "no scanner")() == {"unavailable": "no_feed: no scanner"}


def test_http_json_digs_a_path_and_needs_its_token(monkeypatch):
    fake = FakeHTTP({"api.example.com": {"data": [{"total": 42}]}})
    monkeypatch.setattr(basic, "get_json", fake)
    snap = basic.http_json("leads", "https://api.example.com/x", path="data.0.total", token_env="X_TOKEN")
    assert snap() == {"unavailable": "X_TOKEN not set"}
    monkeypatch.setenv("X_TOKEN", "t")
    assert snap() == {"leads": 42}
    assert fake.calls[-1][2]["Authorization"] == "Bearer t"


@pytest.mark.parametrize("query", [
    "DELETE FROM t", "UPDATE t SET x=1", "SELECT 1; DROP TABLE t", "WITH x AS (SELECT 1) INSERT INTO t SELECT 1",
])
def test_sql_refuses_anything_but_a_single_select(query):
    with pytest.raises(ValueError):
        sql("n", query)


def test_sql_reads_sqlite_read_only(tmp_path):
    db = tmp_path / "f.db"
    con = sqlite3.connect(db)
    con.execute("create table finance(runway int)")
    con.execute("insert into finance values (123)")
    con.commit()
    con.close()
    assert sql("cash_runway_days", "SELECT runway FROM finance", sqlite_path=str(db))() == {"cash_runway_days": 123}


def test_github_change_failure_rate_uses_latest_status_and_skips_unfinished(monkeypatch):
    deployments = [
        {"created_at": "2026-09-20T00:00:00Z", "statuses_url": "https://api.github.com/s/1"},
        {"created_at": "2026-09-21T00:00:00Z", "statuses_url": "https://api.github.com/s/2"},
        {"created_at": "2026-09-22T00:00:00Z", "statuses_url": "https://api.github.com/s/3"},
        {"created_at": "2026-09-23T00:00:00Z", "statuses_url": "https://api.github.com/s/4"},
        {"created_at": "2026-07-01T00:00:00Z", "statuses_url": "https://api.github.com/s/5"},  # out of window
    ]
    fake = FakeHTTP({"/deployments": deployments,
                     "/s/1": [{"state": "success"}], "/s/2": [{"state": "failure"}],
                     "/s/3": [{"state": "in_progress"}], "/s/4": [{"state": "success"}],
                     "/s/5": [{"state": "failure"}]})
    monkeypatch.setattr(github, "get_json", fake)
    out = github.change_failure_rate("acme/web", now=NOW)()
    assert out == {"change_failure_rate_pct": 33.3, "deployments": 3, "failed": 1}


def test_github_ci_pass_rate(monkeypatch):
    runs = {"workflow_runs": [{"conclusion": "success"}, {"conclusion": "failure"},
                              {"conclusion": "success"}, {"conclusion": "cancelled"}]}
    monkeypatch.setattr(github, "get_json", FakeHTTP({"/actions/runs": runs}))
    assert github.ci_pass_rate("acme/web", now=NOW)() == {"ci_pass_rate_pct": 66.7, "runs": 3}


def test_stripe_refuses_secret_keys_and_paginates(monkeypatch):
    monkeypatch.setenv("STRIPE_API_KEY", "sk_live_x")
    assert "restricted" in stripe.revenue_per_day(now=NOW)()["unavailable"]
    monkeypatch.setenv("STRIPE_API_KEY", "rk_live_x")
    pages = iter([
        {"data": [{"id": "a", "type": "charge", "amount": 50000, "currency": "usd"},
                  {"id": "b", "type": "refund", "amount": -5000, "currency": "usd"}], "has_more": True},
        {"data": [{"id": "c", "type": "payment", "amount": 25000, "currency": "usd"},
                  {"id": "d", "type": "charge", "amount": 99999, "currency": "eur"}], "has_more": False},
    ])
    fake = FakeHTTP({"balance_transactions": lambda params: next(pages)})
    monkeypatch.setattr(stripe, "get_json", fake)
    out = stripe.revenue_per_day(days=7, now=NOW)()
    assert out["revenue_per_day"] == round((50000 - 5000 + 25000) / 100 / 7, 2)
    assert fake.calls[1][1]["starting_after"] == "b"
