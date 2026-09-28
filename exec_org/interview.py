"""The company interview: 8 questions (or your company.md) in, a first roster out.

    exec-org interview                      # asks 8 questions
    exec-org interview --from company.md    # reads a company file instead
    exec-org interview --write              # writes exec_roles.py (refuses to overwrite)
    exec-org interview --claude             # Claude polishes each seat's wording (optional)

The roster is deterministic from your answers. Claude, if asked, may only reword the
owned outcome and the fix of seats already chosen; it cannot add seats, numbers or alarms.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, replace

from .catalog import BUSINESS_TYPES, SeatTemplate, pick

QUESTIONS = [
    ("business", f"What kind of business is it? ({'/'.join(BUSINESS_TYPES)})"),
    ("north_star", "Your North Star in a few words (e.g. 'weekly active accounts'), or blank for the default"),
    ("ships_code", "Do you ship software or deploy code at least weekly? (y/n)"),
    ("customer_data", "Do you hold customer data, logins or payment details? (y/n)"),
    ("agents", "Do you run AI agents or automations that can silently stall? (y/n)"),
    ("recurring", "Do customers pay on a recurring basis, so they can churn? (y/n)"),
    ("team", "Do you employ people or contractors you need to hire and keep? (y/n)"),
    ("data_feeds", "Do several of your numbers come from syncs or exports that can go stale? (y/n)"),
]

_KEYWORDS = {
    "business": [("saas", r"\b(saas|subscription software|app)\b"), ("agency", r"\bagency\b"),
                 ("ecommerce", r"\b(e-?commerce|shop|store|orders)\b"),
                 ("content", r"\b(content|seo|publisher|media|newsletter|sites?)\b"),
                 ("services", r"\b(consult|services|freelanc)\w*")],
    "ships_code": r"\b(deploy|ship|engineer|developers?|codebase|repo)\w*",
    "customer_data": r"\b(customer data|pii|payments?|logins?|accounts?|gdpr|hipaa)\b",
    "agents": r"\b(agents?|automations?|workflows?|bots?|claude|llm)\b",
    "recurring": r"\b(subscriptions?|recurring|retainers?|mrr|arr|churn)\b",
    "team": r"\b(team|employees|hire|hiring|staff|contractors)\b",
    "data_feeds": r"\b(sync|export|etl|pipeline|warehouse|dashboard)s?\b",
}


@dataclass
class Answers:
    business: str = "saas"
    north_star: str = ""
    ships_code: bool = True
    customer_data: bool = True
    agents: bool = False
    recurring: bool = False
    team: bool = False
    data_feeds: bool = False


def _yes(v: str) -> bool:
    return v.strip().lower() in {"y", "yes", "true", "1"}


def ask(prompt: Callable[[str], str] = input) -> Answers:
    raw = {key: prompt(f"{q}\n> ") for key, q in QUESTIONS}
    business = raw["business"].strip().lower()
    return Answers(
        business=business if business in BUSINESS_TYPES else "saas",
        north_star=raw["north_star"].strip(),
        **{k: _yes(raw[k]) for k in ("ships_code", "customer_data", "agents", "recurring", "team", "data_feeds")},
    )


def from_text(text: str) -> Answers:
    """Read a company.md (or any description) with simple keyword rules. Edit the result."""
    low = text.lower()
    business = next((b for b, pat in _KEYWORDS["business"] if re.search(pat, low)), "saas")
    m = re.search(r"north star[^\n:]*[:\-]\s*(.+)", text, re.IGNORECASE)
    return Answers(business=business, north_star=(m.group(1).strip() if m else ""),
                   **{k: bool(re.search(_KEYWORDS[k], low))
                      for k in ("ships_code", "customer_data", "agents", "recurring", "team", "data_feeds")})


def roster(a: Answers) -> list[SeatTemplate]:
    """Deterministic: core seats always, others only when your answers say you need them."""
    roles = ["ceo", "cfo", "cro", "cmo", "cpo", "coo"]
    roles += ["cto"] if a.ships_code else []
    roles += ["ciso"] if a.customer_data or a.ships_code else []
    roles += ["cco"] if a.recurring else []
    roles += ["chro"] if a.team else []
    roles += ["cdo"] if a.data_feeds else []
    roles += ["chief_of_staff"] if a.agents else []
    seats = [pick(r, a.business) for r in roles]
    if a.north_star:
        key = re.sub(r"[^a-z0-9]+", "_", a.north_star.lower()).strip("_")[:40] or "north_star"
        seats[0] = replace(seats[0], owned_outcome=f"The North Star: {a.north_star}", number=key)
    return seats


def polish_with_claude(seats: list[SeatTemplate], context: str, client=None,
                       model: str | None = None) -> list[SeatTemplate]:
    """Optional: Claude rewrites ONLY `owned_outcome` and `fix` wording for the chosen seats.

    Anything else it returns (new seats, numbers, alarms) is ignored. Failure → unchanged.
    """
    from .narrate import DEFAULT_MODEL

    if client is None:
        try:
            import anthropic
        except ImportError:
            return seats
        client = anthropic.Anthropic(timeout=60.0, max_retries=2)
    brief = [{"role_id": s.role_id, "owned_outcome": s.owned_outcome, "number": s.number, "fix": s.fix}
             for s in seats]
    try:
        resp = client.messages.create(
            model=model or DEFAULT_MODEL, max_tokens=16000, output_config={"effort": "low"},
            system=("Rewrite each seat's owned_outcome and fix so they fit this company. Keep each under "
                    "12 words, concrete, no jargon. Return ONLY a JSON object mapping role_id to "
                    '{"owned_outcome": str, "fix": str}. Do not add or remove seats.'),
            messages=[{"role": "user", "content": json.dumps({"company": context[:6000], "seats": brief})}])
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        edits: dict[str, dict] = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception:
        return seats
    out = []
    for s in seats:
        e = edits.get(s.role_id) if isinstance(edits, dict) else None
        if isinstance(e, dict):
            s = replace(s, owned_outcome=str(e.get("owned_outcome") or s.owned_outcome)[:120],
                        fix=str(e.get("fix") or s.fix)[:120])
        out.append(s)
    return out


def render(seats: list[SeatTemplate]) -> str:
    """Emit an exec_roles.py the CLI can load. Every seat reads metrics.json until you wire it."""
    order = [s.role_id for s in seats]
    precedence = [r for r in ("cfo", "ciso", "coo", "cto", "cco", "cdo", "cro", "cmo", "cpo", "chro",
                              "chief_of_staff", "ceo") if r in order]
    out = ['"""Your AI executive roster. Generated by `exec-org interview`; edit freely.',
           "",
           "Every seat reads metrics.json until you swap in a real reader (see the hint on each seat).",
           'The rule: one owned outcome, one number."""',
           "",
           "from exec_org.readers import json_file",
           "from exec_org.registry import Registry, Seat, Threshold",
           "",
           f"PRECEDENCE = {tuple(precedence)!r}",
           "",
           "SEATS = ["]
    for s in seats:
        alarm = f"Threshold({s.alarm[0]!r}, {s.alarm[1]!r})" if s.alarm else "None"
        out += [f"    # reader hint: {s.reader_hint}",
                f"    Seat({s.role_id!r}, {s.title!r}, owned_outcome={s.owned_outcome!r},",
                f"         number={s.number!r}, unit={s.unit!r}, better={s.better!r},",
                f"         alarm={alarm}, fix={s.fix!r},",
                f"         snapshot=json_file({s.number!r})),"]
    out += ["]", "", "for _seat in SEATS:", "    Registry.register(_seat)", ""]
    return "\n".join(out)


def metrics_stub(seats: list[SeatTemplate]) -> str:
    return json.dumps({"_comment": "Fill in real numbers, or wire each seat to a reader. null = unavailable.",
                       **{s.number: None for s in seats}}, indent=2) + "\n"
