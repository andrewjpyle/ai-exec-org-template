"""Registry guards: threshold validation, seat validation, safe_snapshot honesty."""

import logging

import pytest

from exec_org.registry import Registry, Seat, Threshold, fix_first, safe_snapshot


def _seat(**kw):
    base = dict(role_id="qa", title="AI QA", owned_outcome="bugs", number="open_bugs")
    base.update(kw)
    return Seat(**base)


def test_threshold_rejects_unknown_op():
    with pytest.raises(ValueError, match="threshold op must be one of"):
        Threshold("==", 3)


def test_threshold_crossed_is_false_for_non_numeric():
    t = Threshold(">=", 5)
    assert t.crossed("n/a") is False
    assert t.crossed(None) is False
    assert t.crossed("7") is True


def test_seat_rejects_bad_better():
    with pytest.raises(ValueError, match="better must be"):
        _seat(better="sideways")


def test_seat_alarm_without_fix_rejected():
    with pytest.raises(ValueError, match="needs a `fix`"):
        _seat(alarm=Threshold(">=", 1))


def test_arm_flag_is_upper_role_id():
    assert _seat(role_id="cfo").arm_flag == "EXEC_CFO_ENABLED"


def test_safe_snapshot_no_snapshot_wired():
    assert safe_snapshot(_seat()) == {"unavailable": "no snapshot wired yet"}


def test_safe_snapshot_swallows_errors_and_logs(caplog):
    def boom():
        raise RuntimeError("x" * 500)

    with caplog.at_level(logging.WARNING, logger="exec_org.registry"):
        snap = safe_snapshot(_seat(snapshot=boom))
    msg = snap["unavailable"]
    assert msg.startswith("snapshot error: RuntimeError: ")
    assert len(msg.split(": ", 2)[2]) == 120  # message truncated
    assert "snapshot for qa failed" in caplog.text


def test_safe_snapshot_empty_dict_is_unavailable():
    assert safe_snapshot(_seat(snapshot=lambda: {})) == {
        "unavailable": "snapshot returned nothing"
    }


def test_safe_snapshot_missing_number_keeps_other_fields():
    snap = safe_snapshot(_seat(snapshot=lambda: {"other": 1, "open_bugs": None}))
    assert snap["unavailable"] == "open_bugs not reported"
    assert snap["other"] == 1


def test_safe_snapshot_passes_good_snapshot_through():
    assert safe_snapshot(_seat(snapshot=lambda: {"open_bugs": 0})) == {"open_bugs": 0}


def test_fix_first_message_and_none_cases():
    seat = _seat(unit=" bugs", alarm=Threshold(">=", 5), fix="triage")
    assert fix_first(seat, {"open_bugs": 9}) == "triage (open_bugs = 9 bugs, alarm >= 5 bugs)"
    assert fix_first(seat, {"open_bugs": 1}) is None
    assert fix_first(seat, {"unavailable": "x"}) is None
    assert fix_first(_seat(), {"open_bugs": 99}) is None


def test_register_requires_outcome_and_number():
    with pytest.raises(ValueError, match="one owned outcome and one number"):
        Registry.register(_seat(owned_outcome=""))
    with pytest.raises(ValueError, match="one owned outcome and one number"):
        Registry.register(_seat(number=""))
