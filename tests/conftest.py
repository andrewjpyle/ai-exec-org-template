import json
from pathlib import Path

import pytest

from exec_org.loader import load_roles
from exec_org.registry import Registry

EXAMPLE_METRICS = Path(__file__).resolve().parent.parent / "examples" / "metrics.example.json"


@pytest.fixture(autouse=True)
def example_roster(monkeypatch, tmp_path):
    """Every test starts from the Acme example roster, nothing armed, in a clean cwd."""
    for var in ("EXEC_ARMED", "EXEC_ROLES", "EXEC_SINK", "EXEC_ARM_BY", "EXEC_CLAUDE_NARRATE",
                "EXEC_ALERT_WEBHOOK", "EXEC_ALERT_GITHUB_REPO", "STRIPE_API_KEY", "GITHUB_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    metrics = tmp_path / "metrics.json"
    metrics.write_text(EXAMPLE_METRICS.read_text())
    monkeypatch.setenv("EXEC_METRICS_FILE", str(metrics))
    module = load_roles()
    yield module
    Registry.clear()


@pytest.fixture
def all_armed():
    return {s.arm_flag: "1" for s in Registry.all()}


@pytest.fixture
def set_metrics(tmp_path):
    def _set(**values):
        path = tmp_path / "metrics.json"
        data = json.loads(path.read_text())
        data.update(values)
        path.write_text(json.dumps(data))
    return _set


class FakeHTTP:
    """Stand-in for readers._http.get_json: maps URL substrings to canned JSON."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, params=None, headers=None, timeout=None):
        self.calls.append((url, params, headers))
        for needle, payload in self.routes.items():
            if needle in url:
                return payload(params) if callable(payload) else payload
        raise AssertionError(f"unexpected URL {url}")
