from types import SimpleNamespace

from exec_org.engine import compose_brief
from exec_org.narrate import grounded, make_narrator
from exec_org.registry import Registry, Seat, Threshold

SEAT = Seat("cto", "AI CTO", owned_outcome="o", number="cfr", unit="%", better="down",
            alarm=Threshold(">=", 15), fix="pause merges")
SNAP = {"cfr": 18.2, "deployments": 40, "failed": 7}


def _client(text, stop="end_turn"):
    resp = SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)])
    create = lambda **kw: resp  # noqa: E731
    calls = []

    def recorder(**kw):
        calls.append(kw)
        return create(**kw)
    client = SimpleNamespace(messages=SimpleNamespace(create=recorder),
                             beta=SimpleNamespace(messages=SimpleNamespace(create=recorder)))
    return client, calls


def test_grounding_drops_any_line_with_a_number_not_in_the_snapshot():
    lines = ["7 of 40 deploys failed, 18.2% against a 15% alarm.",
             "That is up from 11% last month.",            # 11 is invented: dropped
             "Look at which repo the failures cluster in."]
    assert grounded(lines, SEAT, SNAP) == [lines[0], lines[2]]


def test_narrator_is_off_unless_explicitly_enabled(monkeypatch):
    assert make_narrator() is None


def test_narrator_sends_no_tools_and_uses_refusal_fallback_on_opus():
    client, calls = _client("7 of 40 deploys failed.\nInvented 999 widgets.")
    lines = make_narrator(model="claude-opus-5", client=client)(SEAT, SNAP)
    assert lines == ["7 of 40 deploys failed."]
    assert "tools" not in calls[0] and calls[0]["fallbacks"] == "default"


def test_narrator_returns_nothing_on_refusal_or_error():
    client, _ = _client("anything", stop="refusal")
    assert make_narrator(model="claude-opus-5", client=client)(SEAT, SNAP) == []

    def boom(**kw):
        raise ConnectionError("offline")
    broken = SimpleNamespace(messages=SimpleNamespace(create=boom), beta=SimpleNamespace(messages=SimpleNamespace(create=boom)))
    assert make_narrator(model="claude-opus-5", client=broken)(SEAT, SNAP) == []


def test_brief_labels_claudes_lines_as_advisory(all_armed):
    client, _ = _client("Runway is 140 days.")
    narrator = make_narrator(model="claude-opus-5", client=client)
    body = compose_brief(env={Registry.get("cfo").arm_flag: "1"}, narrator=narrator)
    assert "Claude's read (advisory" in body and "Runway is 140 days." in body
