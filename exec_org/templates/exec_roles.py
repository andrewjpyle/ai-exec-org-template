"""Your AI executive roster. Edit freely: this file is yours, not the library's.

Nine example seats for a fictional company (Acme Widgets). Each reads one number from
metrics.json so the first brief runs right away. Swap readers as you wire real data:

    from exec_org.readers import github, stripe, sql, http_json, no_feed
    snapshot=github.change_failure_rate("your-org/your-repo")          # CTO
    snapshot=stripe.revenue_per_day(days=7)                             # CRO
    snapshot=sql("cash_runway_days", "SELECT runway FROM finance_v")    # CFO
    snapshot=no_feed("open_critical_findings", "no scanner wired yet")  # honest gap

The rule: one owned outcome, one number. Arm seats one at a time (EXEC_CFO_ENABLED=1).
"""

from __future__ import annotations

from exec_org.readers import json_file
from exec_org.registry import Registry, Seat, Threshold

# Which seat's alarm becomes "today's one action" first. Existential risks lead.
PRECEDENCE = ("cfo", "ciso", "coo", "cto", "cro", "cmo", "cpo", "chief_of_staff", "ceo")

SEATS = [
    Seat("ceo", "AI CEO", owned_outcome="The North Star: weekly active customers",
         number="weekly_active_customers", better="up",
         alarm=Threshold("<", 1500), fix="Call the five largest customers who went quiet this week",
         reads=["product analytics"], snapshot=json_file("weekly_active_customers")),
    Seat("cfo", "AI CFO", owned_outcome="Cash, debt payoff and cost control",
         number="cash_runway_days", unit=" days", better="up",
         alarm=Threshold("<", 90), fix="Cut or defer the largest non-payroll cost line",
         reads=["accounting export", "bank balances"], snapshot=json_file("cash_runway_days")),
    Seat("cro", "AI CRO", owned_outcome="Revenue per day",
         number="revenue_per_day", unit=" USD/day", better="up",
         alarm=Threshold("<", 2000), fix="Chase the three largest overdue invoices",
         reads=["Stripe", "CRM"], snapshot=json_file("revenue_per_day")),
    Seat("cmo", "AI CMO", owned_outcome="Demand: qualified leads",
         number="weekly_qualified_leads", better="up",
         alarm=Threshold("<", 30), fix="Double down on the channel that sourced the most leads last month",
         reads=["search console", "CRM"], snapshot=json_file("weekly_qualified_leads")),
    Seat("cpo", "AI CPO", owned_outcome="Which products earn their place",
         number="products_flagged_for_review", better="down",
         alarm=Threshold(">=", 5), fix="Retire or rework the lowest-usage flagged product",
         reads=["product analytics"], snapshot=json_file("products_flagged_for_review")),
    Seat("coo", "AI COO", owned_outcome="Runtime operations: uptime and cost to run",
         number="uptime_pct_7d", unit="%", better="up",
         alarm=Threshold("<", 99.5), fix="Fix the service behind the longest outage this week",
         reads=["uptime monitor", "cloud bills"], snapshot=json_file("uptime_pct_7d")),
    Seat("cto", "AI CTO", owned_outcome="Engineering quality: ship healthy, tested, deployable code",
         number="change_failure_rate_pct", unit="%", better="down",
         alarm=Threshold(">=", 15), fix="Pause feature merges on the worst repo until its deploys go green",
         reads=["deploy history", "CI"], snapshot=json_file("change_failure_rate_pct")),
    Seat("ciso", "AI CISO", owned_outcome="Security posture: open critical findings",
         number="open_critical_findings", better="down",
         alarm=Threshold(">=", 1), fix="Close the open critical finding before anything else ships",
         reads=["dependency scanner", "secret scanner"], snapshot=json_file("open_critical_findings")),
    Seat("chief_of_staff", "AI Chief of Staff", owned_outcome="The agent fleet: who is running, what is stuck",
         number="stale_agent_sessions", better="down",
         alarm=Threshold(">=", 5), fix="Close or restart the stale agent sessions",
         reads=["agent session log"], snapshot=json_file("stale_agent_sessions")),
]

for _seat in SEATS:
    Registry.register(_seat)
