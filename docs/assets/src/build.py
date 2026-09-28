"""Build the README graphics: HTML sources here, PNGs one level up.

    python docs/assets/src/build.py            # writes docs/assets/src/*.html
    then render each with any headless Chromium at 2x (see docs/assets/src/README.md)

All data shown is the fictional Acme Widgets sample. Palette: Dark Workshop.
"""

from __future__ import annotations

import html
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent

CSS = """
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,500;1,9..144,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;700&display=block" rel="stylesheet">
<style>
:root{--bg:#0D0D0D;--card:#141312;--line:#2a2724;--ivory:#F4EFE6;--muted:#a39d93;--dim:#6d675f;--amber:#E8912D;--amber-d:#C27F21;--good:#8fbf7a;--bad:#e0735a}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--ivory);font-family:Inter,sans-serif;overflow:hidden}
body{position:relative}
.grain{position:absolute;inset:0;opacity:.06;pointer-events:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='200' height='200'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}
.mono{font-family:'JetBrains Mono',monospace}
*{font-variant-ligatures:none !important;font-feature-settings:'liga' 0,'calt' 0 !important}
.serif{font-family:Fraunces,serif}
.k{font:500 13px 'JetBrains Mono';letter-spacing:.2em;color:var(--amber);text-transform:uppercase}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px}
.pill{font:500 14px 'JetBrains Mono';letter-spacing:.14em;color:var(--amber);border:1.5px solid var(--amber-d);border-radius:999px;padding:9px 20px;display:inline-block}
.foot{position:absolute;bottom:22px;left:48px;right:48px;display:flex;justify-content:space-between;font:500 12px 'JetBrains Mono';letter-spacing:.18em;color:var(--dim)}
.foot b{color:var(--amber);font-weight:500}
</style>
"""

SEATS = [("CEO", "north star"), ("CFO", "cash runway"), ("CRO", "revenue/day"), ("CMO", "qualified leads"),
         ("CPO", "products to review"), ("COO", "uptime"), ("CTO", "change-failure %"),
         ("CISO", "critical findings"), ("CoS", "stale agents")]


def page(w: int, h: int, body: str, title: str) -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(title)}</title>{CSS}"
            f"<style>html,body{{width:{w}px;height:{h}px}}</style></head><body><div class='grain'></div>{body}"
            "<div class='foot'><span>AI-EXEC-ORG-TEMPLATE · SAMPLE DATA: ACME WIDGETS</span><b>/ ANDREWJPYLE.COM</b></div>"
            "</body></html>")


def wheel(size: int, r_nodes: int, node_r: int, center_top: str, center_main: str) -> str:
    c = size / 2
    parts = [f"<svg width='{size}' height='{size}' viewBox='0 0 {size} {size}'>",
             "<defs><radialGradient id='g'><stop offset='0' stop-color='#E8912D' stop-opacity='.35'/>"
             "<stop offset='1' stop-color='#E8912D' stop-opacity='0'/></radialGradient></defs>",
             f"<circle cx='{c}' cy='{c}' r='{r_nodes + node_r + 14}' fill='none' stroke='#2a2724' stroke-dasharray='3 6'/>",
             f"<circle cx='{c}' cy='{c}' r='{int(r_nodes * .62)}' fill='none' stroke='#2a2724'/>"]
    hub = int(size * .16)
    for i, (label, sub) in enumerate(SEATS):
        a = -math.pi / 2 + i * 2 * math.pi / len(SEATS)
        x, y = c + r_nodes * math.cos(a), c + r_nodes * math.sin(a)
        ix, iy = c + hub * math.cos(a), c + hub * math.sin(a)
        ox, oy = x - node_r * math.cos(a), y - node_r * math.sin(a)
        parts.append(f"<line x1='{ix:.1f}' y1='{iy:.1f}' x2='{ox:.1f}' y2='{oy:.1f}' stroke='#8a5a22' stroke-width='1.5'/>")
        parts.append(f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{node_r}' fill='#141312' stroke='#E8912D' stroke-width='1.3'/>"
                     f"<text x='{x:.1f}' y='{y + 5:.1f}' text-anchor='middle' font-family='JetBrains Mono' font-size='{int(node_r * .5)}' "
                     f"font-weight='500' fill='#F4EFE6'>{label}</text>")
    parts.append(f"<circle cx='{c}' cy='{c}' r='{hub + 18}' fill='url(#g)'/>"
                 f"<circle cx='{c}' cy='{c}' r='{hub}' fill='#17120c' stroke='#E8912D' stroke-width='1.6'/>"
                 f"<text x='{c}' y='{c - 8}' text-anchor='middle' font-family='JetBrains Mono' font-size='12' letter-spacing='2' fill='#a39d93'>{center_top}</text>"
                 f"<text x='{c}' y='{c + 22}' text-anchor='middle' font-family='Fraunces' font-size='{int(hub * .36)}' fill='#F4EFE6'>{center_main}</text>")
    parts.append("</svg>")
    return "".join(parts)


def hero() -> str:
    rules = [("01", "One outcome, one number", "Every seat owns one thing and one number that measures it."),
             ("02", "Drafts only", "One engine writes one brief a human reads. Nothing executes."),
             ("03", "Dead-man on its own channel", "If the brief stops landing, a separate job says so.")]
    rules_html = "".join(
        f"<div style='display:flex;gap:16px;margin-top:22px'><div class='mono' style='color:var(--amber);font-size:14px;padding-top:4px'>{n}</div>"
        f"<div><div style='font-size:21px;font-weight:600'>{t}</div><div style='color:var(--muted);font-size:16px;margin-top:5px;line-height:1.4'>{d}</div></div></div>"
        for n, t, d in rules)
    body = f"""
<div style='position:absolute;left:64px;top:64px;width:640px'>
  <div class='k'>AI-EXEC-ORG-TEMPLATE · OPEN SOURCE · MIT</div>
  <h1 class='serif' style='font-weight:500;font-size:64px;line-height:1.02;margin-top:22px'>An AI executive team<br><em style='font-weight:400;color:var(--amber)'>that cannot act.</em></h1>
  <div style='margin-top:18px;font-size:19px;color:var(--muted);line-height:1.45'>Nine seats read your real numbers. One engine writes one draft brief a day, with <b style='color:var(--ivory);font-weight:600'>today's one action</b> on top. You decide.</div>
  {rules_html}
  <div class='pill' style='margin-top:30px'>9 SEATS · 1 ENGINE · 2 DEAD-MEN · 0 AUTONOMOUS ACTIONS</div>
</div>
<div style='position:absolute;right:56px;top:70px'>{wheel(540, 208, 40, 'DAILY BRIEF', 'Draft')}</div>
"""
    return page(1400, 760, body, "hero")


def architecture() -> str:
    def box(x, y, w, h, title, lines, accent=False):
        border = "var(--amber)" if accent else "var(--line)"
        bg = "#17120c" if accent else "var(--card)"
        li = "".join(f"<div class='mono' style='font-size:13px;color:var(--muted);margin-top:6px'>{html.escape(t)}</div>" for t in lines)
        return (f"<div style='position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;background:{bg};border:1.5px solid {border};"
                f"border-radius:12px;padding:16px 18px'><div class='k' style='font-size:12px'>{title}</div>{li}</div>")

    def arrow(x1, y1, x2, y2, label="", dashed=False, side="above"):
        dash = "stroke-dasharray='6 6'" if dashed else ""
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if not label:
            lab = ""
        elif side == "right":
            lab = (f"<text x='{mx + 14}' y='{my + 4}' font-family='JetBrains Mono' font-size='12' fill='#a39d93'>{label}</text>")
        else:
            lab = (f"<text x='{mx}' y='{my - 14}' text-anchor='middle' font-family='JetBrains Mono' font-size='12' fill='#a39d93'>{label}</text>")
        return (f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#C27F21' stroke-width='2' {dash} marker-end='url(#a)'/>{lab}")

    svg = ("<svg style='position:absolute;inset:0' width='1400' height='760'><defs><marker id='a' markerWidth='10' markerHeight='10' "
           "refX='8' refY='5' orient='auto'><path d='M0,0 L10,5 L0,10 z' fill='#C27F21'/></marker></defs>"
           + arrow(276, 300, 356, 300)
           + arrow(586, 300, 666, 300)
           + arrow(896, 300, 976, 300)
           + arrow(1091, 380, 1091, 568, "a human reads", side="right")
           + arrow(446, 628, 616, 628, "no brief in 26h", dashed=True)
           + arrow(846, 628, 976, 628, "to you", dashed=True)
           + "</svg>")
    body = f"""
<div style='position:absolute;left:56px;top:48px'><div class='k'>HOW IT WORKS</div>
<div class='serif' style='font-size:40px;margin-top:10px'>Read, compose, <em style='color:var(--amber)'>draft</em>. Never act.</div></div>
{svg}
<div class='mono' style='position:absolute;left:56px;top:150px;font-size:13px;color:var(--dim)'>readers are GET / SELECT only &#183; the engine writes one draft &#183; the dead-man runs on its own schedule</div>
{box(56, 190, 220, 220, "READERS", ["github: deploys, CI", "stripe: revenue", "sql: SELECT only", "http_json: any API", "no_feed: honest gap"])}
{box(366, 190, 220, 220, "9 SEATS", ["one outcome", "one number", "one alarm", "one fix", "dormant until armed"])}
{box(676, 190, 220, 220, "ONE ENGINE", ["snapshot per seat", "deltas vs last brief", "CEO arbitration:", "today's one action", "blind seats flagged"], True)}
{box(986, 220, 230, 160, "SINK", ["file / GitHub issue", "Slack webhook", "a place people read"])}
{box(986, 578, 230, 100, "YOU", ["read, decide, act"], True)}
{box(216, 578, 230, 100, "DEAD-MAN", ["own schedule, own job", "checks the sink"])}
{box(626, 578, 220, 100, "ALERT CHANNEL", ["exec-alert issue", "or a webhook"])}
"""
    return page(1400, 760, body, "architecture")


def anatomy() -> str:
    lines = [
        ("h1", "AI Executive Daily Brief (DRAFT) · 2026-09-28"),
        ("q", "Draft only. Nothing in this brief has been executed. A human reads it and decides."),
        ("h2", "Today's one action"),
        ("b", "Close the open critical finding before anything else ships (open_critical_findings = 1, alarm >= 1)"),
        ("i", "Owner: AI CISO. Why: AI CISO is #2 in precedence and its alarm fired."),
        ("h2", "AI CFO"),
        ("li", "cash_runway_days: 140 days <span style='color:var(--bad)'>▼ -10 days vs last brief, worse</span>"),
        ("li", "Fix first: nothing. Alarm fires at &lt; 90 days"),
        ("h2", "AI CTO"),
        ("li", "change_failure_rate_pct: 18.2% <span style='color:var(--bad)'>▲ +6.2% vs last brief, worse</span>"),
        ("li", "Fix first: Pause feature merges on the worst repo until its deploys go green"),
        ("li", "Claude's read (advisory, numbers checked against the snapshot):"),
        ("li2", "18.2% is above the 15% alarm. Check which repo the failures cluster in."),
        ("h2", "AI CRO"),
        ("li", "revenue_per_day: <span style='color:var(--amber)'>unavailable (STRIPE_API_KEY not set)</span>"),
        ("m", "&lt;!-- exec-metrics:v1 {\"cfo\": 140, \"cto\": 18.2, \"ciso\": 1} --&gt;"),
    ]
    style = {"h1": "font:500 26px Fraunces;margin:4px 0 10px", "q": "color:var(--muted);border-left:3px solid var(--line);padding-left:12px;margin-bottom:14px",
             "h2": "font:600 17px Inter;margin:14px 0 6px;color:var(--ivory)", "b": "font-weight:600;color:var(--amber)",
             "i": "color:var(--muted);font-style:italic;margin-top:4px", "li": "margin:4px 0 0 16px", "li2": "margin:3px 0 0 36px;color:var(--muted)",
             "m": "margin-top:14px;color:var(--dim);font:12px 'JetBrains Mono'"}
    doc = "".join(f"<div style=\"font-size:15px;line-height:1.45;{style[k]}\">{t}</div>" for k, t in lines)
    notes = [(212, "The engine picks ONE action across all seats, in precedence order."),
             (304, "Deltas know which way is good for each number."),
             (420, "Every alarm has one concrete fix a human can do today."),
             (454, "Optional Claude read: no tools, any number not in the snapshot is dropped."),
             (528, "Can't read it? It says so. Never a fake 0."),
             (562, "Invisible marker: tomorrow's brief reads it for deltas.")]
    callouts = "".join(
        f"<div style='position:absolute;left:870px;top:{y}px;width:470px;display:flex;gap:12px;align-items:flex-start'>"
        f"<div style='width:26px;height:2px;background:var(--amber);margin-top:11px;flex:none'></div>"
        f"<div style='font-size:16px;line-height:1.4'>{t}</div></div>" for y, t in notes)
    body = f"""
<div style='position:absolute;left:56px;top:40px'><div class='k'>ANATOMY OF A BRIEF</div></div>
<div class='card' style='position:absolute;left:56px;top:80px;width:780px;padding:22px 26px'>{doc}</div>
{callouts}
"""
    return page(1400, 760, body, "anatomy")


def timeline() -> str:
    steps = [("13:30", "Engine runs", "One job loops every armed seat. Snapshots are read-only.", False),
             ("13:31", "Draft filed", "One brief lands where a human reads it: an issue, a file, Slack.", False),
             ("Anytime", "You decide", "Today's one action is on top. You act, or you don't.", True),
             ("16:10", "Dead-man checks", "A separate job looks for today's brief. Different schedule, different channel.", False),
             ("If missing", "Alert fires", "The engine stalled. You hear about it the same day, not next week.", False)]
    items = "".join(
        f"<div style='position:relative;width:236px'>"
        f"<div style='width:18px;height:18px;border-radius:50%;background:{'var(--amber)' if hl else '#17120c'};border:2px solid var(--amber);margin:0 auto'></div>"
        f"<div class='mono' style='text-align:center;margin-top:16px;color:var(--amber);font-size:14px;letter-spacing:.1em'>{t}</div>"
        f"<div style='text-align:center;font-size:20px;font-weight:600;margin-top:8px'>{h}</div>"
        f"<div style='text-align:center;color:var(--muted);font-size:15px;line-height:1.45;margin-top:8px;padding:0 8px'>{d}</div></div>"
        for t, h, d, hl in steps)
    body = f"""
<div style='position:absolute;left:56px;top:56px'><div class='k'>ONE ENGINE, TWO DEAD-MEN</div>
<div class='serif' style='font-size:42px;margin-top:12px'>A day in the life of the brief</div>
<div style='color:var(--muted);font-size:18px;margin-top:10px;max-width:900px;line-height:1.45'>The second dead-man nudges you when seats are built but never switched on. Built-and-forgotten is its own silent failure.</div></div>
<div style='position:absolute;left:70px;right:70px;top:440px;height:2px;background:linear-gradient(90deg,var(--amber-d),var(--line))'></div>
<div style='position:absolute;left:56px;right:56px;top:431px;display:flex;justify-content:space-between'>{items}</div>
"""
    return page(1400, 760, body, "timeline")


def catalog() -> str:
    from exec_org.catalog import CATALOG, pick  # noqa: E402

    order = ["ceo", "cfo", "cro", "cmo", "cpo", "coo", "cto", "ciso", "chief_of_staff", "cco", "chro", "cdo"]
    cards = []
    for rid in order:
        t = pick(rid, "saas")
        alarm = f"alarm {t.alarm[0]} {t.alarm[1]:g}{t.unit}" if t.alarm else "no default alarm"
        cards.append(
            f"<div class='card' style='padding:16px 18px;height:150px'><div class='k' style='font-size:12px'>{html.escape(t.title)}</div>"
            f"<div style='font-size:16px;margin-top:10px;line-height:1.3;height:42px'>{html.escape(t.owned_outcome)}</div>"
            f"<div class='mono' style='font-size:13px;color:var(--ivory);margin-top:10px'>{t.number}</div>"
            f"<div class='mono' style='font-size:12px;color:var(--dim);margin-top:5px'>{html.escape(alarm)}</div></div>")
    body = f"""
<div style='position:absolute;left:56px;top:48px'><div class='k'>THE SEAT CATALOG</div>
<div class='serif' style='font-size:40px;margin-top:10px'>12 seats. One outcome, one number each.</div>
<div style='color:var(--muted);font-size:17px;margin-top:8px'><span class='mono' style='color:var(--ivory)'>exec-org interview</span> picks the ones your business needs, with variants for 5 business types.</div></div>
<div style='position:absolute;left:56px;right:56px;top:196px;display:grid;grid-template-columns:repeat(4,1fr);gap:14px'>{''.join(cards)}</div>
"""
    return page(1400, 760, body, "catalog")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(HERE.parents[2]))
    for name, fn in [("hero", hero), ("architecture", architecture), ("anatomy", anatomy),
                     ("timeline", timeline), ("catalog", catalog)]:
        (HERE / f"{name}.html").write_text(fn(), encoding="utf-8")
        print("wrote", HERE / f"{name}.html")
