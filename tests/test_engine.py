from datetime import datetime, timezone

import pytest

from exec_org.arbitration import one_action
from exec_org.engine import compose_brief, previous_metrics, run_daily_brief
from exec_org.registry import Registry, Seat, Threshold, is_armed, safe_snapshot
from exec_org.sinks import FileSink


def test_nine_seats_each_with_one_outcome_and_one_number():
    seats = Registry.all()
    assert len(seats) == 9
    assert {s.role_id for s in seats} >= {"ceo", "cfo", "cro", "cmo", "cpo", "coo", "cto", "ciso", "chief_of_staff"}
    assert all(s.owned_outcome and s.number for s in seats)
    assert len({s.arm_flag for s in seats}) == 9


def test_registry_refuses_a_seat_without_a_number_or_an_alarm_without_a_fix():
    with pytest.raises(ValueError):
        Registry.register(Seat("vague", "AI Vague", owned_outcome="help out", number=""))
    with pytest.raises(ValueError):
        Seat("x", "AI X", owned_outcome="o", number="n", alarm=Threshold(">", 1))


def test_every_seat_ships_dormant_and_arms_one_at_a_time():
    assert not any(is_armed(s, env={}) for s in Registry.all())
    armed = [s.role_id for s in Registry.all() if is_armed(s, {"EXEC_CFO_ENABLED": "1"})]
    assert armed == ["cfo"]
    armed = [s.role_id for s in Registry.all() if is_armed(s, {"EXEC_ARMED": "cfo, cto"})]
    assert sorted(armed) == ["cfo", "cto"]


def test_engine_self_silences_with_nothing_armed(tmp_path):
    assert compose_brief(env={}) is None
    assert run_daily_brief(sink=FileSink(tmp_path / "b"), env={})["written"] is False
    assert not (tmp_path / "b").exists()


def test_brief_is_a_draft_with_one_action_and_a_metrics_marker(all_armed):
    body = compose_brief(env=all_armed, now=datetime(2026, 9, 28, tzinfo=timezone.utc))
    assert "(DRAFT)" in body and "Nothing in this brief has been executed" in body
    assert "## Today's one action" in body
    # Acme sample: CISO has 1 open critical finding and outranks the CTO's 18.2% failure rate.
    assert "Close the open critical finding" in body.split("## AI CEO")[0]
    assert previous_metrics(body)["cto"] == 18.2


def test_deltas_compare_against_the_previous_brief_and_know_which_way_is_good(all_armed):
    prev = '<!-- exec-metrics:v1 {"cfo": 150, "cto": 12.0} -->'
    body = compose_brief(env=all_armed, previous=prev)
    assert "140 days (▼ -10 days vs last brief, worse)" in body
    assert "18.2% (▲ +6.2% vs last brief, worse)" in body
    assert "(no prior reading)" in body          # seats with no previous value


def test_unreadable_number_is_unavailable_never_zero(all_armed, set_metrics):
    set_metrics(revenue_per_day=None)
    body = compose_brief(env=all_armed)
    assert "**revenue_per_day**: unavailable (revenue_per_day not reported)" in body
    assert '"cro"' not in body.split("exec-metrics:v1")[1]   # an unknown is not written as a reading


def test_broken_snapshot_reports_unavailable_instead_of_raising():
    def boom():
        raise RuntimeError("db down")
    seat = Seat("x", "AI X", owned_outcome="o", number="n", snapshot=boom)
    assert safe_snapshot(seat)["unavailable"].startswith("snapshot error: RuntimeError")


def test_arbitration_never_reports_all_clear_over_blind_seats():
    ok = Seat("cfo", "AI CFO", owned_outcome="o", number="runway", alarm=Threshold("<", 90), fix="cut")
    blind = Seat("ciso", "AI CISO", owned_outcome="o", number="findings", alarm=Threshold(">=", 1), fix="close")
    d = one_action([(ok, {"runway": 200}), (blind, {"unavailable": "no_feed: scanner"})])
    assert d.owner is None and "AI CISO" in d.action and d.blind == ["AI CISO"]


def test_arbitration_follows_precedence():
    a = Seat("cto", "AI CTO", owned_outcome="o", number="cfr", alarm=Threshold(">=", 15), fix="pause merges")
    b = Seat("cfo", "AI CFO", owned_outcome="o", number="runway", alarm=Threshold("<", 90), fix="cut costs")
    readings = [(a, {"cfr": 20}), (b, {"runway": 30})]
    assert one_action(readings).owner == "AI CFO"
    assert one_action(readings, precedence=["cto", "cfo"]).owner == "AI CTO"


def test_all_clear_when_every_seat_is_readable_and_inside_its_alarm():
    s = Seat("cfo", "AI CFO", owned_outcome="o", number="runway", alarm=Threshold("<", 90), fix="cut")
    assert one_action([(s, {"runway": 200})]).action.startswith("Nothing is over threshold")


def test_run_daily_brief_writes_once_and_reads_back_deltas(tmp_path, all_armed):
    sink = FileSink(tmp_path / "briefs")
    first = run_daily_brief(sink=sink, env=all_armed)
    assert first["written"] and first["location"].endswith(".md")
    assert previous_metrics(sink.latest()[1])["cfo"] == 140
