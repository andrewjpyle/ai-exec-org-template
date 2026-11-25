"""Edge cases for the engine: marker parsing, delta text, brief lines, sink failure."""

from datetime import datetime, timezone

from exec_org.engine import _fmt, compose_brief, delta_text, previous_metrics, run_daily_brief
from exec_org.registry import Registry, Seat, Threshold
from exec_org.sinks import FileSink


def _seat(role="zed", better="up", **kw):
    return Seat(role, f"AI {role.upper()}", owned_outcome="o", number="n", better=better,
                unit=kw.pop("unit", "%"), **kw)


def test_fmt_keeps_bools_and_strings_and_trims_numbers():
    assert _fmt(True) == "True"
    assert _fmt("abc") == "abc"
    assert _fmt(1234.0) == "1,234"
    assert _fmt(2.50) == "2.5"
    assert _fmt(1234.567) == "1,234.57"


def test_previous_metrics_handles_empty_missing_and_broken_markers():
    assert previous_metrics(None) == {}
    assert previous_metrics("") == {}
    assert previous_metrics("no marker here") == {}
    assert previous_metrics("<!-- exec-metrics:v1 {not json} -->") == {}
    assert previous_metrics('x <!-- exec-metrics:v1 {"a": 1} --> y') == {"a": 1}


def test_delta_text_covers_flat_missing_and_both_directions():
    up, down = _seat(better="up"), _seat(better="down")
    assert delta_text(up, 5, None) == "(no prior reading)"
    assert delta_text(up, "x", 5) == "(no prior reading)"
    assert delta_text(up, 5, 5) == "(= flat vs last brief)"
    assert delta_text(up, 7, 5) == "(▲ +2% vs last brief, better)"
    assert delta_text(up, 3, 5) == "(▼ -2% vs last brief, worse)"
    assert delta_text(down, 7, 5) == "(▲ +2% vs last brief, worse)"
    assert delta_text(down, 3, 5) == "(▼ -2% vs last brief, better)"


def test_brief_lines_for_each_seat_state():
    Registry.clear()
    Registry.register(_seat("noalarm", snapshot=lambda: {"n": 4, "note": "hi"}))
    Registry.register(_seat("blind", alarm=Threshold(">", 1), fix="Fix it",
                            snapshot=lambda: {"unavailable": "api down"}))
    Registry.register(_seat("quiet", alarm=Threshold(">", 10), fix="Act",
                            snapshot=lambda: {"n": 3}))
    Registry.register(_seat("loud", alarm=Threshold(">", 1), fix="Act now",
                            snapshot=lambda: {"n": 9}))
    Registry.register(_seat("text", snapshot=lambda: {"n": "green"}))
    Registry.register(_seat("flag", snapshot=lambda: {"n": True}))
    env = {"EXEC_ARMED": "noalarm,blind,quiet,loud,text,flag"}
    body = compose_brief(env=env, now=datetime(2026, 1, 2, tzinfo=timezone.utc))
    assert "· 2026-01-02" in body
    assert "- **n**: unavailable (api down)" in body
    assert "- Fix first: no alarm set for this seat" in body
    assert "- Fix first: blind (the number is unreadable, so the alarm cannot be judged)" in body
    assert "  - note: hi" in body
    assert "- Fix first: nothing. Alarm fires at > 10%" in body
    assert "- Fix first: Act now (n = 9%, alarm > 1%)" in body
    assert "_Owner: AI LOUD. Why: AI LOUD is #" in body
    # a non-numeric headline is printed but never stored as a metric
    assert previous_metrics(body) == {"loud": 9, "noalarm": 4, "quiet": 3}


def test_decision_without_owner_prints_why_only():
    Registry.clear()
    Registry.register(_seat("solo", alarm=Threshold(">", 10), fix="Act",
                            snapshot=lambda: {"n": 1}))
    body = compose_brief(env={"EXEC_ARMED": "solo"})
    assert "_Why: every armed seat was readable and inside its threshold._" in body
    assert "_Owner:" not in body


def test_narrator_runs_only_for_readable_seats_and_empty_reads_are_dropped():
    Registry.clear()
    Registry.register(_seat("ok", snapshot=lambda: {"n": 1}))
    Registry.register(_seat("empty", snapshot=lambda: {"n": 2}))
    Registry.register(_seat("blind", snapshot=lambda: {"unavailable": "x"}))
    seen = []

    def narrator(seat, snap):
        seen.append(seat.role_id)
        return ["line one", "line two"] if seat.role_id == "ok" else []

    body = compose_brief(env={"EXEC_ARMED": "ok,empty,blind"}, narrator=narrator)
    assert sorted(seen) == ["empty", "ok"]
    assert body.count("Claude's read") == 1
    assert "  - line one" in body and "  - line two" in body


def test_run_daily_brief_survives_an_unreadable_sink(tmp_path):
    Registry.clear()
    Registry.register(_seat("ok", snapshot=lambda: {"n": 1}))

    class BrokenRead(FileSink):
        def latest(self):
            raise OSError("cannot read")

    result = run_daily_brief(sink=BrokenRead(tmp_path / "b"), env={"EXEC_ARMED": "ok"})
    assert result["written"] is True
    assert result["armed"] == ["ok"]
    assert "no prior reading" in (tmp_path / "b").glob("*.md").__next__().read_text()
