import json
import os
from datetime import date, datetime, timedelta, timezone

import pytest

from exec_org import roles  # noqa: F401  (registers the example seats)
from exec_org.deadman import check_brief_stalled, check_unarmed
from exec_org.engine import compose_brief, run_daily_brief
from exec_org.registry import Registry, Seat, is_armed, safe_snapshot
from exec_org.sinks import FileSink

ALL_ARMED = {s.arm_flag: "1" for s in Registry.all()}


def test_seven_example_seats_each_with_one_outcome_and_one_number():
    seats = Registry.all()
    assert len(seats) == 7
    assert all(s.owned_outcome and s.number for s in seats)


def test_a_seat_without_a_number_is_refused():
    with pytest.raises(ValueError):
        Registry.register(Seat("vague", "AI Vague", owned_outcome="help out", number=""))


def test_every_seat_ships_dormant():
    assert not any(is_armed(s, env={}) for s in Registry.all())


def test_seats_arm_one_at_a_time():
    cfo = Registry.get("cfo")
    env = {"EXEC_CFO_ENABLED": "1"}
    assert is_armed(cfo, env)
    assert [s.role_id for s in Registry.all() if is_armed(s, env)] == ["cfo"]


def test_engine_self_silences_with_nothing_armed(tmp_path):
    assert compose_brief(env={}) is None
    assert run_daily_brief(sink=FileSink(tmp_path), env={})["written"] is False
    assert not list(tmp_path.iterdir())


def test_brief_is_a_draft_with_real_numbers_and_honest_gaps(tmp_path, monkeypatch):
    metrics = tmp_path / "metrics.json"
    metrics.write_text(json.dumps({"cash_runway_days": 90}))
    monkeypatch.setenv("EXEC_METRICS_FILE", str(metrics))
    body = compose_brief(env={"EXEC_CFO_ENABLED": "1", "EXEC_CRO_ENABLED": "1"})
    assert "(DRAFT)" in body and "Nothing in this brief has been executed" in body
    assert "**cash_runway_days**: 90" in body
    assert "unavailable: revenue_per_day not reported" in body  # never fabricated


def test_broken_snapshot_reports_unavailable_instead_of_raising():
    def boom():
        raise RuntimeError("db down")
    seat = Seat("x", "AI X", owned_outcome="o", number="n", snapshot=boom)
    assert safe_snapshot(seat) == {"unavailable": "snapshot error: RuntimeError"}


def test_stall_deadman_quiet_when_fresh_loud_when_stale(tmp_path, monkeypatch):
    monkeypatch.setenv("EXEC_METRICS_FILE", str(tmp_path / "none.json"))
    sink = FileSink(tmp_path)
    assert check_brief_stalled(sink=sink, env={}) is None  # nothing armed: not a stall
    assert "never" in check_brief_stalled(sink=sink, env=ALL_ARMED)
    path = sink.write("x")
    assert check_brief_stalled(sink=sink, env=ALL_ARMED) is None
    old = (datetime.now(timezone.utc) - timedelta(hours=30)).timestamp()
    os.utime(path, (old, old))
    assert "STALLED" in check_brief_stalled(sink=sink, env=ALL_ARMED)


def test_unarmed_deadman_only_after_the_deadline():
    env = {"EXEC_ARM_BY": "2026-10-01"}
    assert check_unarmed(env={}, today=date(2027, 1, 1)) is None  # no deadline set
    assert check_unarmed(env=env, today=date(2026, 9, 30)) is None
    assert "not armed" in check_unarmed(env=env, today=date(2026, 10, 2))
    assert check_unarmed(env={**env, **ALL_ARMED}, today=date(2026, 10, 2)) is None
