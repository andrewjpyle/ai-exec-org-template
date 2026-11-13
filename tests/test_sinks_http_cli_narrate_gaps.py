"""Coverage for the network sinks, the HTTP helper, the CLI paths and the narrator guards.

No test touches the network: urllib.request.urlopen and get_json are replaced.
"""
import io
import json
import logging
import sys
from datetime import timezone
from types import SimpleNamespace

import pytest

from exec_org import narrate, sinks
from exec_org.cli import main
from exec_org.readers import _http
from exec_org.registry import Seat, Threshold
from exec_org.sinks import FileSink, GitHubIssueSink, MultiSink, SlackSink, from_env


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _urlopen(body, seen):
    def fake(req, timeout=None):
        seen.append((req, timeout))
        return _Resp(body)
    return fake


# ---- readers/_http.py ----

def test_get_json_appends_params_and_sends_headers(monkeypatch):
    seen = []
    monkeypatch.setattr(_http.urllib.request, "urlopen", _urlopen(b'{"a": 1}', seen))
    assert _http.get_json("https://x.test/p", params={"q": [1, 2]}, headers={"X-K": "v"}) == {"a": 1}
    req, timeout = seen[0]
    assert req.full_url == "https://x.test/p?q=1&q=2"
    assert req.get_method() == "GET" and req.get_header("X-k") == "v"
    assert req.get_header("User-agent") == _http.USER_AGENT and timeout == _http.TIMEOUT_SECONDS
    assert _http.get_json("https://x.test/p?z=1", params={"q": 1}) == {"a": 1}
    assert seen[1][0].full_url == "https://x.test/p?z=1&q=1"


def test_get_json_empty_body_is_none(monkeypatch):
    monkeypatch.setattr(_http.urllib.request, "urlopen", _urlopen(b"", []))
    assert _http.get_json("https://x.test") is None


def test_dig_walks_lists_and_dicts_and_raises_on_scalars():
    assert _http.dig({"data": [{"total": 5}]}, "data.0.total") == 5
    assert _http.dig({"a": 1}, "") == {"a": 1}
    with pytest.raises(KeyError):
        _http.dig({"a": 1}, "a.b")


# ---- sinks ----

def test_post_json_sends_a_post_and_tolerates_non_json(monkeypatch):
    seen = []
    monkeypatch.setattr(sinks.urllib.request, "urlopen", _urlopen(b"ok", seen))
    assert sinks._post_json("https://h.test", {"t": 1}, {"X-A": "b"}) == {"raw": "ok"}
    req, timeout = seen[0]
    assert req.get_method() == "POST" and json.loads(req.data) == {"t": 1}
    assert req.get_header("X-a") == "b" and req.get_header("Content-type") == "application/json"
    monkeypatch.setattr(sinks.urllib.request, "urlopen", _urlopen(b"", []))
    assert sinks._post_json("https://h.test", {}) == {}


def test_slack_sink_posts_title_and_body_and_never_reads(monkeypatch):
    posted = []
    monkeypatch.setattr(sinks, "_post_json", lambda url, payload, headers=None: posted.append((url, payload)) or {})
    monkeypatch.setenv("EXEC_SLACK_WEBHOOK", "https://hooks.test/x")
    s = SlackSink()
    assert s.write("body", "Title") == "slack" and s.write("only") == "slack"
    assert posted[0] == ("https://hooks.test/x", {"text": "*Title*\nbody"})
    assert posted[1][1] == {"text": "only"}
    assert s.latest() is None


def test_slack_sink_needs_its_webhook():
    with pytest.raises(ValueError, match="EXEC_SLACK_WEBHOOK"):
        SlackSink()


def test_github_sink_needs_a_repo(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)
    monkeypatch.delenv("EXEC_GITHUB_REPO", raising=False)
    with pytest.raises(ValueError, match="repo"):
        GitHubIssueSink()


def test_github_sink_writes_an_issue_and_reads_the_latest(monkeypatch):
    posted = []
    monkeypatch.setenv("GITHUB_TOKEN", "tok")
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setattr(sinks, "_post_json", lambda url, payload, headers=None: posted.append((url, payload, headers))
                        or {"html_url": "https://gh.test/1"})
    g = GitHubIssueSink()
    assert g.write("b", "t") == "https://gh.test/1"
    url, payload, headers = posted[0]
    assert url.endswith("/repos/o/r/issues") and payload["labels"] == ["exec-brief"]
    assert headers["Authorization"] == "Bearer tok"

    monkeypatch.setattr(sinks, "get_json", lambda url, params=None, headers=None: [
        {"created_at": "2026-10-01T12:00:00Z", "body": "hello"}])
    when, body = g.latest()
    assert when.tzinfo is not None and when.utcoffset() == timezone.utc.utcoffset(when)
    assert (when.year, when.month, when.day, when.hour) == (2026, 10, 1, 12) and body == "hello"
    monkeypatch.setattr(sinks, "get_json", lambda *a, **k: [{"created_at": "2026-10-01T12:00:00Z", "body": None}])
    assert g.latest()[1] == ""
    monkeypatch.setattr(sinks, "get_json", lambda *a, **k: [])
    assert g.latest() is None


def test_github_sink_prefers_exec_repo_over_actions_repo(monkeypatch):
    monkeypatch.setenv("EXEC_GITHUB_REPO", "mine/x")
    monkeypatch.setenv("GITHUB_REPOSITORY", "other/y")
    assert GitHubIssueSink().repo == "mine/x"


def test_multisink_writes_to_all_and_reads_from_the_first(tmp_path):
    a, b = FileSink(tmp_path / "a"), FileSink(tmp_path / "b")
    m = MultiSink(a, b)
    out = m.write("x")
    assert out.count(", ") == 1 and (tmp_path / "a").exists() and (tmp_path / "b").exists()
    assert m.latest()[1] == "x"
    b.write("newer")                                  # second sink differs: latest() must come from the first
    assert m.latest()[1] == "x"
    with pytest.raises(ValueError):
        MultiSink()


def test_from_env_picks_and_rejects_sinks(monkeypatch, tmp_path):
    monkeypatch.setenv("EXEC_SLACK_WEBHOOK", "https://hooks.test/x")
    assert isinstance(from_env(), FileSink)
    assert isinstance(from_env(" FILE , slack "), MultiSink)
    monkeypatch.setenv("EXEC_SINK", "slack")
    assert isinstance(from_env(), SlackSink)
    with pytest.raises(ValueError, match="unknown sink"):
        from_env("file,carrier-pigeon")


def test_file_sink_latest_is_none_when_the_directory_is_missing_or_empty(tmp_path):
    assert FileSink(tmp_path / "nope").latest() is None
    (tmp_path / "empty").mkdir()
    assert FileSink(tmp_path / "empty").latest() is None


# ---- cli ----

def test_cli_seats_lists_armed_and_dormant(capsys, monkeypatch):
    monkeypatch.setenv("EXEC_ARMED", "cfo")
    assert main(["seats"]) == 0
    out = capsys.readouterr().out
    assert "ARMED" in out and "dormant" in out


def test_cli_with_no_command_prints_help_and_exits_2(capsys):
    assert main([]) == 2
    assert "usage" in capsys.readouterr().out.lower()


def test_cli_brief_dry_run_with_nothing_armed_says_how_to_arm(capsys):
    assert main(["brief", "--dry-run"]) == 0
    assert "No seats armed" in capsys.readouterr().out


def test_cli_brief_writes_to_the_sink(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EXEC_ARMED", "cfo")
    monkeypatch.setenv("EXEC_BRIEF_DIR", str(tmp_path / "briefs"))
    assert main(["brief"]) == 0
    capsys.readouterr()
    assert list((tmp_path / "briefs").glob("brief_*.md"))


def test_cli_deadman_quiet_then_fires(capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("EXEC_BRIEF_DIR", str(tmp_path / "briefs"))
    assert main(["deadman"]) == 0
    assert "quiet" in capsys.readouterr().out
    monkeypatch.setenv("EXEC_ARMED", "cfo")           # armed, but no brief was ever written
    assert main(["deadman"]) == 1
    assert "STALLED" in capsys.readouterr().out


def test_cli_init_keeps_existing_files_without_force(capsys, tmp_path):
    target = tmp_path / "repo"
    assert main(["init", str(target), "--no-actions"]) == 0
    assert "wrote" in capsys.readouterr().out
    assert main(["init", str(target), "--no-actions"]) == 0
    assert "kept" in capsys.readouterr().out
    assert main(["init", str(target), "--no-actions", "--force"]) == 0
    assert "kept" not in capsys.readouterr().out


COMPANY = "# Acme\nWe run a SaaS app with subscriptions. North star: weekly active teams\n"


def test_cli_interview_prints_without_writing(capsys, tmp_path):
    f = tmp_path / "company.md"
    f.write_text(COMPANY)
    assert main(["interview", "--from", str(f)]) == 0
    out = capsys.readouterr().out
    assert "--write" in out and "seats for a saas business" in out
    assert not (tmp_path / "exec_roles.py").exists()


def test_cli_interview_reply_prints_the_first_three_seats(capsys, tmp_path):
    f = tmp_path / "company.md"
    f.write_text(COMPANY)
    assert main(["interview", "--from", str(f), "--reply"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("Your first three AI seats") and "--write" not in out


def test_cli_interview_write_respects_force(capsys, tmp_path):
    f = tmp_path / "company.md"
    f.write_text(COMPANY)
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    import os
    os.chdir(out_dir)
    assert main(["interview", "--from", str(f), "--write"]) == 0
    assert (out_dir / "exec_roles.py").exists() and (out_dir / "metrics.json").exists()
    (out_dir / "exec_roles.py").write_text("# mine")
    assert main(["interview", "--from", str(f), "--write"]) == 0
    assert "kept" in capsys.readouterr().out
    assert (out_dir / "exec_roles.py").read_text() == "# mine"
    assert main(["interview", "--from", str(f), "--write", "--force"]) == 0
    assert (out_dir / "exec_roles.py").read_text() != "# mine"


def test_cli_interview_claude_flag_runs_the_polish_step(capsys, tmp_path, monkeypatch):
    f = tmp_path / "company.md"
    f.write_text(COMPANY)
    seen = {}
    from exec_org import interview as iv

    def fake_polish(seats, context):
        seen["context"] = context
        return seats[:2]
    monkeypatch.setattr(iv, "polish_with_claude", fake_polish)
    assert main(["interview", "--from", str(f), "--claude"]) == 0
    assert "2 seats for a saas" in capsys.readouterr().out and "weekly active teams" in seen["context"]


def test_cli_interview_asks_questions_when_no_file(capsys, monkeypatch):
    from exec_org import interview as iv
    monkeypatch.setattr(iv, "ask", lambda: iv.Answers(business="agency"))
    assert main(["interview"]) == 0
    assert "agency business" in capsys.readouterr().out


def test_python_dash_m_entrypoint_calls_main(monkeypatch):
    import runpy
    monkeypatch.setattr(sys, "argv", ["exec-org", "--version"])
    with pytest.raises(SystemExit) as e:
        runpy.run_module("exec_org", run_name="__main__")
    assert e.value.code == 0


# ---- narrate ----

SEAT = Seat("cto", "AI CTO", owned_outcome="o", number="cfr", unit="%", better="down",
            alarm=Threshold(">=", 15), fix="pause merges")


def test_canon_returns_none_for_a_non_number():
    assert narrate._canon("1,2.x") is None
    assert narrate._canon("1,234.5") == 1234.5


def test_allowed_numbers_reads_nested_values_strings_and_the_alarm():
    snap = {"a": 3, "flag": True, "s": "up 1,200 from 80", "nest": {"l": [2.456, (9,)]}}
    ok = narrate.allowed_numbers(SEAT, snap)
    assert {3.0, 1200.0, 80.0, 2.456, 2.46, 2.5, 9.0, 15.0} <= ok
    assert 1.0 not in ok          # bool True must not whitelist the number 1


def test_grounded_caps_the_line_count(monkeypatch):
    lines = [f"{i} deploys" for i in range(10)]
    snap = {"n": list(range(10))}
    assert len(narrate.grounded(lines, SEAT, snap)) == narrate.MAX_LINES


def test_grounded_logs_a_dropped_line(caplog):
    with caplog.at_level(logging.INFO, logger=narrate.logger.name):
        assert narrate.grounded(["99 invented"], SEAT, {"n": 1}) == []
    assert "dropped an ungrounded line" in caplog.text


def test_make_narrator_is_off_by_default_and_on_with_the_flag_but_no_sdk(monkeypatch, caplog):
    assert narrate.make_narrator() is None
    monkeypatch.setenv("EXEC_CLAUDE_NARRATE", "yes")
    monkeypatch.setitem(sys.modules, "anthropic", None)      # makes `import anthropic` raise ImportError
    with caplog.at_level(logging.WARNING, logger=narrate.logger.name):
        assert narrate.make_narrator() is None
    assert "not installed" in caplog.text


def test_make_narrator_builds_a_client_when_the_sdk_is_present(monkeypatch):
    made = {}

    class FakeAnthropic:
        def __init__(self, **kw):
            made.update(kw)
            self.messages = SimpleNamespace(create=lambda **k: SimpleNamespace(
                stop_reason="end_turn", content=[SimpleNamespace(type="text", text="- 18 percent")]))
    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeAnthropic))
    monkeypatch.setenv("EXEC_CLAUDE_NARRATE", "1")
    monkeypatch.setenv("EXEC_CLAUDE_MODEL", "some-model")
    n = narrate.make_narrator()
    assert made == {"timeout": 60.0, "max_retries": 2}
    assert n(SEAT, {"cfr": 18}) == ["18 percent"]


def test_narrator_swallows_api_errors_and_refusals(caplog):
    def boom(**kw):
        raise RuntimeError("api down")
    client = SimpleNamespace(messages=SimpleNamespace(create=boom))
    n = narrate.make_narrator(model="m", client=client)
    with caplog.at_level(logging.WARNING, logger=narrate.logger.name):
        assert n(SEAT, {"cfr": 18}) == []
    assert "RuntimeError" in caplog.text
    refusal = SimpleNamespace(stop_reason="refusal", content=[SimpleNamespace(type="text", text="18")])
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: refusal))
    assert narrate.make_narrator(model="m", client=client)(SEAT, {"cfr": 18}) == []
