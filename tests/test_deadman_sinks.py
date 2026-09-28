import os
from datetime import date, datetime, timedelta, timezone

import pytest

from exec_org import deadman
from exec_org.deadman import check_brief_stalled, check_unarmed
from exec_org.sinks import FileSink, GitHubIssueSink, MultiSink, from_env


def test_stall_deadman_quiet_when_fresh_loud_when_stale(tmp_path, all_armed):
    sink = FileSink(tmp_path / "b")
    assert check_brief_stalled(sink=sink, env={}) is None           # nothing armed: not a stall
    assert "never" in check_brief_stalled(sink=sink, env=all_armed)
    path = sink.write("x")
    assert check_brief_stalled(sink=sink, env=all_armed) is None
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).timestamp()
    os.utime(path, (old, old))
    assert "STALLED" in check_brief_stalled(sink=sink, env=all_armed)


def test_stall_deadman_treats_an_unreadable_sink_as_stalled(all_armed):
    class Broken:
        def latest(self):
            raise ConnectionError("down")
    assert "cannot read the brief sink" in check_brief_stalled(sink=Broken(), env=all_armed)


def test_unarmed_deadman_only_after_the_deadline(all_armed):
    env = {"EXEC_ARM_BY": "2026-10-01"}
    assert check_unarmed(env={}, today=date(2027, 1, 1)) is None
    assert check_unarmed(env=env, today=date(2026, 9, 30)) is None
    assert "not armed" in check_unarmed(env=env, today=date(2026, 10, 2))
    assert check_unarmed(env={**env, **all_armed}, today=date(2026, 10, 2)) is None


def test_alert_goes_to_its_own_channel(monkeypatch, capsys):
    posted = []
    monkeypatch.setattr(deadman, "_post_json", lambda url, payload, headers=None: posted.append((url, payload)))
    assert deadman.alert("boom") == "stderr" and "ALERT: boom" in capsys.readouterr().err
    monkeypatch.setenv("EXEC_ALERT_GITHUB_REPO", "acme/ops")
    assert deadman.alert("boom") == "github-issue" and posted[-1][1]["labels"] == ["exec-alert"]
    monkeypatch.setenv("EXEC_ALERT_WEBHOOK", "https://hooks.example.com/x")
    assert deadman.alert("boom") == "webhook" and posted[-1][0] == "https://hooks.example.com/x"


def test_github_issue_sink_writes_a_labeled_issue_and_reads_the_latest(monkeypatch):
    import exec_org.sinks as sinks
    posted = []
    monkeypatch.setattr(sinks, "_post_json", lambda url, payload, headers=None: posted.append(payload) or {"html_url": "u"})
    monkeypatch.setattr(sinks, "get_json", lambda url, params=None, headers=None: [
        {"created_at": "2026-09-28T13:30:00Z", "body": "hello"}])
    sink = GitHubIssueSink("acme/ops")
    assert sink.write("body", "title") == "u" and posted[0]["labels"] == ["exec-brief"]
    when, body = sink.latest()
    assert body == "hello" and when.tzinfo is not None


def test_from_env_builds_sinks_and_rejects_unknown(monkeypatch, tmp_path):
    assert isinstance(from_env("file"), FileSink)
    monkeypatch.setenv("EXEC_SLACK_WEBHOOK", "https://hooks.example.com/x")
    assert isinstance(from_env("file,slack"), MultiSink)
    with pytest.raises(ValueError):
        from_env("fax")
