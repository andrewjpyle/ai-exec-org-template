import json
from pathlib import Path
from types import SimpleNamespace

from exec_org import interview as iv
from exec_org.cli import main
from exec_org.loader import load_roles
from exec_org.registry import Registry
from exec_org.scaffold import scaffold


def test_interview_answers_drive_a_deterministic_roster():
    lean = iv.roster(iv.Answers(business="agency", ships_code=False, customer_data=False))
    assert [s.role_id for s in lean] == ["ceo", "cfo", "cro", "cmo", "cpo", "coo"]
    assert lean[2].number == "pipeline_value" and lean[5].number == "projects_overdue"
    full = iv.roster(iv.Answers(business="saas", north_star="weekly active teams", agents=True,
                                recurring=True, team=True, data_feeds=True))
    assert {"cto", "ciso", "cco", "chro", "cdo", "chief_of_staff"} <= {s.role_id for s in full}
    assert full[0].number == "weekly_active_teams"


def test_interview_reads_a_company_file():
    a = iv.from_text("# Acme\nWe run a SaaS app with subscriptions. North star: weekly active teams\n"
                     "Small team of engineers who deploy daily. We store customer data.")
    assert a.business == "saas" and a.recurring and a.ships_code and a.customer_data
    assert a.north_star == "weekly active teams"


def test_rendered_roster_loads_and_every_seat_starts_unavailable(tmp_path, monkeypatch):
    seats = iv.roster(iv.Answers(business="ecommerce", recurring=True))
    (tmp_path / "exec_roles.py").write_text(iv.render(seats))
    (tmp_path / "metrics.json").write_text(iv.metrics_stub(seats))
    monkeypatch.setenv("EXEC_METRICS_FILE", str(tmp_path / "metrics.json"))
    module = load_roles(str(tmp_path / "exec_roles.py"))
    assert len(Registry.all()) == len(seats) and module.PRECEDENCE[0] == "cfo"
    assert all("unavailable" in s.snapshot() for s in Registry.all())


def test_claude_polish_may_only_reword_outcome_and_fix():
    seats = iv.roster(iv.Answers(business="saas", ships_code=False, customer_data=False))
    edits = {"cfo": {"owned_outcome": "Stay funded", "fix": "Cut the SaaS tools nobody opened",
                     "number": "HACKED", "alarm": [">", 0]},
             "new_seat": {"owned_outcome": "x"}}
    resp = SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(edits))])
    client = SimpleNamespace(messages=SimpleNamespace(create=lambda **kw: resp))
    out = iv.polish_with_claude(seats, "context", client=client)
    cfo = next(s for s in out if s.role_id == "cfo")
    assert cfo.owned_outcome == "Stay funded" and cfo.number == "cash_runway_days" and cfo.alarm == ("<", 90)
    assert len(out) == len(seats)


def test_init_scaffolds_everything_and_never_clobbers(tmp_path):
    repo = tmp_path / "repo"
    written, skipped = scaffold(repo)
    names = {str(p.relative_to(repo)) for p in written}
    assert {"exec_roles.py", "metrics.json", "CLAUDE.md", ".claude/skills/exec-seat/SKILL.md",
            ".github/workflows/exec-brief.yml", ".github/workflows/exec-deadman.yml"} == names
    (repo / "exec_roles.py").write_text("# mine")
    _, skipped = scaffold(repo)
    assert repo / "exec_roles.py" in skipped and (repo / "exec_roles.py").read_text() == "# mine"


def test_cli_end_to_end_init_then_dry_run_brief(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EXEC_METRICS_FILE", str(tmp_path / "metrics.json"))
    assert main(["init", "."]) == 0
    assert main(["seats"]) == 0
    assert "dormant" in capsys.readouterr().out
    monkeypatch.setenv("EXEC_ARMED", "cfo,cto,ciso")
    assert main(["brief", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "## AI CISO" in out and "## AI CRO" not in out and "Close the open critical finding" in out
    assert not Path("briefs").exists()        # dry run writes nothing
    assert main(["brief"]) == 0
    assert list(Path("briefs").glob("brief_*.md"))
    assert main(["deadman"]) == 0             # a brief just landed: quiet
