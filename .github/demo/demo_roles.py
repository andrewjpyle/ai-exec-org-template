"""The LIVE demo roster this repo runs on itself (see .github/workflows/demo-brief.yml).

One seat reads real data: the AI CTO reads THIS repository's actual GitHub Actions pass rate on
`main`, through the read-only GitHub reader. Every other seat reads the fictional Acme sample in
examples/metrics.example.json, and each brief says so. The briefs land as issues labeled
`exec-brief`; open the Issues tab to read them.
"""

from exec_org.readers import github, json_file
from exec_org.registry import Registry, Seat, Threshold

PRECEDENCE = ("cfo", "ciso", "coo", "cto", "cro", "cmo", "cpo", "chief_of_staff", "ceo")
REPO = "andrewjpyle/ai-exec-org-template"


def sample(key):
    return json_file(key, path="examples/metrics.example.json")


SEATS = [
    Seat("ceo", "AI CEO (sample data)", owned_outcome="The North Star: weekly active customers",
         number="weekly_active_customers", alarm=Threshold("<", 1500),
         fix="Call the five largest customers who went quiet this week", snapshot=sample("weekly_active_customers")),
    Seat("cfo", "AI CFO (sample data)", owned_outcome="Cash, debt payoff and cost control",
         number="cash_runway_days", unit=" days", alarm=Threshold("<", 90),
         fix="Cut or defer the largest non-payroll cost line", snapshot=sample("cash_runway_days")),
    Seat("cto", "AI CTO (LIVE: this repo)", owned_outcome="Engineering quality: main stays green",
         number="ci_pass_rate_pct", unit="%", better="up", alarm=Threshold("<", 90),
         fix="Fix the failing check on main before merging anything else",
         snapshot=github.ci_pass_rate(REPO, branch="main", days=30)),
    Seat("ciso", "AI CISO (sample data)", owned_outcome="Security posture: open critical findings",
         number="open_critical_findings", better="down", alarm=Threshold(">=", 1),
         fix="Close the open critical finding before anything else ships", snapshot=sample("open_critical_findings")),
]

for _seat in SEATS:
    Registry.register(_seat)
