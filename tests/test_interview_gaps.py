import builtins
import json
from types import SimpleNamespace

from exec_org import interview as iv


def _client(text=None, boom=False):
    def create(**kw):
        if boom:
            raise RuntimeError("api down")
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)])
    return SimpleNamespace(messages=SimpleNamespace(create=create))


def _seats():
    return iv.roster(iv.Answers(business="saas", ships_code=False, customer_data=False))


def test_yes_accepts_common_spellings_and_rejects_the_rest():
    for v in ("y", " YES ", "True", "1"):
        assert iv._yes(v) is True
    for v in ("n", "no", "", "maybe", "0"):
        assert iv._yes(v) is False


def test_ask_maps_eight_answers_and_falls_back_on_unknown_business():
    asked = []
    answers = iter(["Agency", "  weekly signups ", "y", "n", "yes", "", "1", "nope"])

    def fake(prompt):
        asked.append(prompt)
        return next(answers)

    a = iv.ask(fake)
    assert len(asked) == len(iv.QUESTIONS) and all(p.endswith("\n> ") for p in asked)
    assert a.business == "agency" and a.north_star == "weekly signups"
    assert (a.ships_code, a.customer_data, a.agents, a.recurring, a.team, a.data_feeds) == (
        True, False, True, False, True, False)
    odd = iter(["spaceship"] + [""] * 7)
    assert iv.ask(lambda p: next(odd)).business == "saas"


def test_polish_without_anthropic_returns_seats_unchanged(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *a, **kw):
        if name == "anthropic":
            raise ImportError(name)
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    seats = _seats()
    assert iv.polish_with_claude(seats, "ctx") is seats


def test_polish_failure_or_garbage_leaves_seats_unchanged():
    seats = _seats()
    assert iv.polish_with_claude(seats, "ctx", client=_client(boom=True)) is seats
    assert iv.polish_with_claude(seats, "ctx", client=_client(text="no json here")) is seats


def test_polish_ignores_non_dict_entries_and_truncates_long_text():
    seats = _seats()
    edits = {"cfo": "just a string", "cro": {"owned_outcome": "x" * 500, "fix": ""}}
    out = iv.polish_with_claude(seats, "ctx", client=_client(text=json.dumps(edits)))
    by = {s.role_id: s for s in out}
    orig = {s.role_id: s for s in seats}
    assert by["cfo"] == orig["cfo"]
    assert len(by["cro"].owned_outcome) == 120
    assert by["cro"].fix == orig["cro"].fix          # empty fix keeps the original


def test_first_three_and_reply_are_grounded_in_the_roster():
    a = iv.Answers(business="content", ships_code=False, customer_data=False)
    seats = iv.first_three(a)
    assert [s.role_id for s in seats] == ["ceo", "cro", "cmo"]
    text = iv.reply(a, seats, repo="https://example.test/repo")
    assert "(content)" in text and "https://example.test/repo" in text
    assert text.count("fix when it fires:") == 3 and "Nothing acts on its own." in text
