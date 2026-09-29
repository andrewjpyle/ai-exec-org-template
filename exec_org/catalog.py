"""The seat catalog: tested starting points for 12 seats across 5 kinds of business.

Each entry is a SUGGESTION of one outcome and one number, with a sensible alarm, the one
action to take when it fires, and the reader most people wire it to. The interview picks
from here; you edit the result.
"""

from __future__ import annotations

from dataclasses import dataclass

BUSINESS_TYPES = ("saas", "agency", "ecommerce", "content", "services")


@dataclass(frozen=True)
class SeatTemplate:
    role_id: str
    title: str
    owned_outcome: str
    number: str
    unit: str
    better: str
    alarm: tuple[str, float] | None
    fix: str
    reader_hint: str


def _t(role_id, title, outcome, number, unit, better, alarm, fix, hint):
    return SeatTemplate(role_id, title, outcome, number, unit, better, alarm, fix, hint)


# role_id -> business type (or "*") -> template
CATALOG: dict[str, dict[str, SeatTemplate]] = {
    "ceo": {
        "saas": _t("ceo", "AI CEO", "The North Star: weekly active accounts", "weekly_active_accounts", "", "up",
                   None, "Talk to the accounts that went quiet this week", "readers.sql / product analytics"),
        "ecommerce": _t("ceo", "AI CEO", "The North Star: weekly orders", "weekly_orders", "", "up",
                        None, "Find why the biggest traffic source converted less", "readers.stripe or shop API"),
        "content": _t("ceo", "AI CEO", "The North Star: weekly organic clicks", "weekly_organic_clicks", "", "up",
                      None, "Look at the pages that lost the most clicks", "search console export"),
        "agency": _t("ceo", "AI CEO", "The North Star: active retainer clients", "active_clients", "", "up",
                     None, "Check in with the client whose work slipped most this month", "CRM via readers.http_json"),
        "services": _t("ceo", "AI CEO", "The North Star: billable hours delivered per week", "billable_hours_weekly", "", "up",
                       None, "Find what pulled the team off billable work this week", "time tracker via readers.http_json"),
        "*": _t("ceo", "AI CEO", "The North Star metric", "north_star", "", "up",
                None, "Revisit the one input that moves the North Star most", "readers.json_file"),
    },
    "cfo": {
        "*": _t("cfo", "AI CFO", "Cash, debt payoff and cost control", "cash_runway_days", " days", "up",
                ("<", 90), "Cut or defer the largest non-payroll cost line", "readers.sql over an accounting export"),
    },
    "cro": {
        "saas": _t("cro", "AI CRO", "Recurring revenue", "mrr", " USD", "up",
                   None, "Chase the largest expansion or recovery opportunity", "readers.stripe / billing API"),
        "agency": _t("cro", "AI CRO", "Signed work in the pipeline", "pipeline_value", " USD", "up",
                     None, "Follow up on the three largest open proposals", "CRM via readers.http_json"),
        "services": _t("cro", "AI CRO", "Signed work in the pipeline", "pipeline_value", " USD", "up",
                       None, "Follow up on the three largest open proposals", "CRM via readers.http_json"),
        "ecommerce": _t("cro", "AI CRO", "Revenue per day", "revenue_per_day", " USD/day", "up",
                        None, "Recover abandoned carts from the biggest traffic source", "readers.stripe.revenue_per_day"),
        "*": _t("cro", "AI CRO", "Revenue per day", "revenue_per_day", " USD/day", "up",
                None, "Chase the three largest overdue invoices", "readers.stripe.revenue_per_day"),
    },
    "cmo": {
        "content": _t("cmo", "AI CMO", "Demand: pages that earn their index slot", "pages_losing_clicks", "", "down",
                      (">=", 25), "Refresh or noindex the worst decaying pages", "search console export"),
        "*": _t("cmo", "AI CMO", "Demand: qualified leads", "weekly_qualified_leads", "", "up",
                None, "Double down on the channel that sourced the most leads last month", "CRM via readers.http_json"),
    },
    "cpo": {
        "*": _t("cpo", "AI CPO", "Which products earn their place", "products_flagged_for_review", "", "down",
                (">=", 5), "Retire or rework the lowest-usage flagged product", "product analytics"),
    },
    "coo": {
        "agency": _t("coo", "AI COO", "Delivery: projects shipped on time", "projects_overdue", "", "down",
                     (">=", 2), "Unblock the most overdue project today", "project tool via readers.http_json"),
        "services": _t("coo", "AI COO", "Delivery: engagements on schedule", "engagements_overdue", "", "down",
                       (">=", 2), "Unblock the most overdue engagement today", "project tool via readers.http_json"),
        "*": _t("coo", "AI COO", "Runtime operations: uptime and cost to run", "uptime_pct_7d", "%", "up",
                ("<", 99.5), "Fix the service behind the longest outage this week", "uptime monitor API"),
    },
    "cto": {
        "*": _t("cto", "AI CTO", "Engineering quality: ship healthy, tested, deployable code",
                "change_failure_rate_pct", "%", "down", (">=", 15),
                "Pause feature merges on the worst repo until its deploys go green",
                "readers.github.change_failure_rate"),
    },
    "ciso": {
        "*": _t("ciso", "AI CISO", "Security posture: open critical findings", "open_critical_findings", "", "down",
                (">=", 1), "Close the open critical finding before anything else ships",
                "dependency / secret scanner export, or readers.no_feed until one exists"),
    },
    "chief_of_staff": {
        "*": _t("chief_of_staff", "AI Chief of Staff", "The agent fleet: who is running, what is stuck",
                "stale_agent_sessions", "", "down", (">=", 5), "Close or restart the stale agent sessions",
                "your agent or automation run log"),
    },
    "cco": {
        "*": _t("cco", "AI CCO", "Customers who stay", "monthly_churn_pct", "%", "down",
                (">=", 3), "Call every account that churned or downgraded this month", "billing via readers.stripe"),
    },
    "chro": {
        "*": _t("chro", "AI CHRO", "A team that stays and grows", "open_roles_over_60d", "", "down",
                (">=", 1), "Rescope or re-post the role open longest", "HR / ATS export"),
    },
    "cdo": {
        "*": _t("cdo", "AI CDO", "Numbers you can trust", "stale_data_feeds", "", "down",
                (">=", 1), "Fix the stalest feed before trusting any seat that reads it", "your ETL / sync logs"),
    },
}


def pick(role_id: str, business: str) -> SeatTemplate:
    options = CATALOG[role_id]
    return options.get(business) or options["*"]
