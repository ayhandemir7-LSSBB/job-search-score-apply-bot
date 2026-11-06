"""HTML renderers and styling, after the Lovable app: navy header, Fit/Win tick gauges,
fit-tier colours, chips, and the full analysis on the back of each card."""
import datetime as dt
import re
from html import escape
from urllib.parse import quote

import gradio as gr

import candidate as C
from scoring import company_tier, fit_tier, win_tier

CSS = """
:root{--jm-navy:#1A3C5E;--jm-teal:#2A7DA0;--jm-gold:#C9841A;--jm-ink:#1f2a37;--jm-muted:#5b6876;--jm-line:#dfe5eb;
--jm-card:#ffffff;--jm-soft:#f3f6f9;--jm-strong:#2e7d5b;--jm-adjacent:#b26a12;--jm-mismatch:#a23b3b}
.dark{--jm-teal:#4aa3c8;--jm-gold:#e3a540;--jm-ink:#e6ebf0;--jm-muted:#a3afbb;--jm-line:#2b3947;--jm-card:#16202b;
--jm-soft:#1c2834;--jm-strong:#4fb489;--jm-adjacent:#e0a24a;--jm-mismatch:#e07a7a}
.gradio-container{max-width:1280px!important}
.jm-header{background:var(--jm-navy);color:#fff;padding:18px 24px;border-radius:8px}
.jm-header h1{margin:0;font-size:21px;font-weight:600;color:#fff}
.jm-header p{margin:4px 0 0;font-size:13px;opacity:.85;color:#fff}
.jm-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:14px}
.jm-card{background:var(--jm-card);border:1px solid var(--jm-line);border-top:4px solid var(--accent);border-radius:10px;
padding:16px;display:flex;flex-direction:column;gap:10px;color:var(--jm-ink);font-size:13px}
.jm-gauges{display:grid;grid-template-columns:1fr 1fr;gap:10px;border-radius:6px;padding:12px 10px;
background:color-mix(in srgb,var(--accent) 13%,transparent)}
.jm-gauge{display:flex;flex-direction:column;align-items:center;padding:0 10px}
.jm-num{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:34px;font-weight:600;line-height:1;font-variant-numeric:tabular-nums}
.jm-ticks{position:relative;height:10px;width:100%;margin-top:8px;display:flex;justify-content:space-between;align-items:flex-end}
.jm-ticks span{display:block;width:1px;height:4px;background:currentColor;opacity:.22}
.jm-ticks span.major{height:7px;opacity:.4}
.jm-ticks i{position:absolute;bottom:0;width:2px;height:10px}
.jm-label{font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:9px;letter-spacing:.08em;text-transform:uppercase;
color:var(--jm-muted);margin-top:6px}
.jm-title{font-weight:600;font-size:15px;line-height:1.3}
.jm-sub{color:var(--jm-muted);font-size:12.5px}
.jm-row{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.jm-chip{border-radius:999px;padding:3px 10px;font-size:11px;font-weight:600}
.jm-badge{border:1px solid var(--jm-line);border-radius:5px;padding:2px 7px;font-size:11px;color:var(--jm-ink);background:var(--jm-card)}
.jm-badge.warn{border-color:var(--jm-mismatch);color:var(--jm-mismatch)}
.jm-stage{background:var(--jm-soft);border-radius:5px;padding:2px 8px;font-size:11px;font-weight:600}
.jm-p{margin:0;font-size:12.5px;line-height:1.45;color:var(--jm-ink)}
.jm-list{border-left:3px solid var(--c);background:color-mix(in srgb,var(--c) 8%,transparent);border-radius:6px;padding:8px 10px;margin:6px 0}
.jm-list h4,.jm-h4{margin:0 0 4px;font:600 9px 'IBM Plex Mono',ui-monospace,monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--c,var(--jm-muted))}
.jm-list ul{margin:0;padding-left:16px}.jm-list li{margin:2px 0;font-size:12.5px}
.jm-meta{display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;margin:6px 0}
.jm-meta dt{font:600 9px 'IBM Plex Mono',monospace;letter-spacing:.08em;text-transform:uppercase;color:var(--jm-muted)}
.jm-meta dd{margin:0;font-size:12px;font-weight:500}
.jm-tags{display:flex;flex-wrap:wrap;gap:4px;margin:4px 0}
.jm-tags span{background:var(--jm-soft);border-radius:4px;padding:1px 6px;font-size:11px}
details.jm-more summary{cursor:pointer;font-size:12px;font-weight:600;color:var(--jm-teal);margin-top:2px}
.jm-cite{font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:var(--jm-teal)}
.jm-panel{background:var(--jm-card);border:1px solid var(--jm-line);border-radius:10px;padding:14px 16px;color:var(--jm-ink)}
.jm-table{width:100%;border-collapse:collapse;font-size:12px}
.jm-table th{text-align:left;background:var(--jm-navy);color:#fff;padding:6px 8px;font-weight:600}
.jm-table td{border-bottom:1px solid var(--jm-line);padding:6px 8px;vertical-align:top}
.jm-kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(128px,1fr));gap:10px}
.jm-kpi{background:var(--jm-card);border:1px solid var(--jm-line);border-radius:8px;padding:12px 14px}
.jm-kpi .v{font:600 22px 'IBM Plex Mono',monospace;color:var(--jm-ink);font-variant-numeric:tabular-nums;overflow-wrap:anywhere}
.jm-kpi .l{font-size:12px;color:var(--jm-muted)}
.jm-links a{display:inline-block;border:1px solid var(--jm-line);border-radius:6px;padding:6px 10px;margin:0 6px 6px 0;
font-size:13px;color:var(--jm-navy);background:var(--jm-card);text-decoration:none}
.dark .jm-links a{color:var(--jm-ink)}
.jm-note{font-size:12px;color:var(--jm-muted);margin:6px 0 0}
.jm-empty{text-align:center;color:var(--jm-muted);padding:30px;font-size:13px}
"""

FIT_COLOR = {"strong": "var(--jm-strong)", "adjacent": "var(--jm-adjacent)", "mismatch": "var(--jm-mismatch)"}
FIT_LABEL = {"strong": "Strong fit", "adjacent": "Adjacent", "mismatch": "Mismatch"}
SOURCE_LABEL = {"artifact-history": "From artifact history", "rag+llm": "RAG + LLM", "offline": "Offline keyword score"}


def theme():
    return gr.themes.Base(
        primary_hue="blue", neutral_hue="slate", radius_size=gr.themes.sizes.radius_sm,
        font=[gr.themes.GoogleFont("IBM Plex Sans"), "ui-sans-serif", "system-ui", "sans-serif"],
        font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "ui-monospace", "monospace"],
    ).set(
        body_background_fill="#f6f8fa", body_background_fill_dark="#0f1720",
        button_primary_background_fill="#1A3C5E", button_primary_background_fill_hover="#24507a",
        button_primary_text_color="#ffffff", button_primary_background_fill_dark="#2A7DA0",
        button_primary_background_fill_hover_dark="#3590b6", color_accent="#2A7DA0", color_accent_soft="#e7f0f5",
    )


def header():
    return ('<div class="jm-header"><h1>Job Match Studio</h1><p>Fit is how well the role matches you. '
            'Win is where you land against the likely shortlist. Scores are grounded in your own Drive documents.</p></div>')


def gauge(value, color, label):
    ticks = "".join(f'<span class="{"major" if i % 5 == 0 else ""}"></span>' for i in range(21))
    if value is None:
        return (f'<div class="jm-gauge" style="color:var(--jm-muted)"><div class="jm-num">—</div>'
                f'<div class="jm-ticks">{ticks}</div><div class="jm-label">{label}</div></div>')
    return (f'<div class="jm-gauge" style="color:{color}"><div class="jm-num">{value}</div>'
            f'<div class="jm-ticks">{ticks}<i style="left:calc({max(0, min(100, value))}% - 1px);background:{color}"></i></div>'
            f'<div class="jm-label">{label}</div></div>')


def _list(title, items, color):
    if not items:
        return ""
    lis = "".join(f"<li>{_cites(escape(str(i)))}</li>" for i in items)
    return f'<div class="jm-list" style="--c:{color}"><h4>{title}</h4><ul>{lis}</ul></div>'


def _cites(text):  # style the [E#] citations
    return re.sub(r"\[(E\d+(?:, E\d+)*)\]", r'<span class="jm-cite">[\1]</span>', text)


def _tags(title, items):
    if not items:
        return ""
    return f'<div class="jm-h4">{title}</div><div class="jm-tags">' + "".join(f"<span>{escape(str(i))}</span>" for i in items) + "</div>"


def pipeline_summary(job):
    if not job.get("applied_on"):
        return "No application date set"
    applied = dt.date.fromisoformat(job["applied_on"])
    end = dt.date.fromisoformat(job["last_activity"]) if job.get("last_activity") else dt.date.today()
    days = max(0, (end - applied).days)
    when = f"{applied.day} {applied:%b}"
    if job.get("last_activity") and job.get("sub_status") in ("rejected", "withdrawn", "offer"):
        return f"Applied {when} · {'offer' if job['sub_status'] == 'offer' else 'closed'} after {days} days"
    return f"Applied {when} · {days} days ago" if days < 30 else f"Applied {when} · no reply in {days} days"


def card(job):
    ai = job.get("ai") or {}
    fit = job.get("fit") or 0
    tier = fit_tier(fit)
    accent = FIT_COLOR[tier]
    top = f'<div class="jm-gauges">{gauge(fit, accent, "Fit")}{gauge(job.get("win"), "var(--jm-gold)", "Win")}</div>'
    head = (f'<div><div class="jm-title">{escape(job["title"])}</div><div class="jm-sub">{escape(job["company"])}</div>'
            f'<div class="jm-sub" style="font-size:11.5px">{escape(job.get("location") or "—")}</div></div>')
    stage = ""
    if job.get("status") == "saved":
        label = C.SUBSTATUS_LABEL.get(job.get("sub_status"), "Stage not set")
        stage = f'<div class="jm-row"><span class="jm-stage">{label}</span><span class="jm-sub">{pipeline_summary(job)}</span></div>'
    chips = (f'<div class="jm-row"><span class="jm-chip" style="background:color-mix(in srgb,{accent} 16%,transparent);color:{accent}">'
             f'{FIT_LABEL[tier]}</span>' + (f'<span class="jm-badge">{escape(ai["pillar"])}</span>' if ai.get("pillar") else "") +
             (f'<span class="jm-badge">{win_tier(job["win"])}</span>' if job.get("win") is not None else "") + "</div>")
    text = (f'<p class="jm-p">{escape(ai.get("summary", ""))}</p>' if ai.get("summary") else "") + \
           (f'<p class="jm-p"><b>Who beats him:</b> {escape(ai["winWhy"])}</p>' if ai.get("winWhy") else "")
    t = company_tier(job["company"])
    badges = [C.TIER_LABEL[t]] if t != "other" else []
    badges += [ai.get("roleType"), C.LEVEL_LABEL.get(ai.get("levelBand"), "")]
    badges += [f"Evidence: {ai['evidence']}"] if ai.get("evidence") else []
    badge_html = "".join(f'<span class="jm-badge">{escape(b)}</span>' for b in badges if b)
    badge_html += '<span class="jm-badge warn">DE required</span>' if ai.get("germanRequired") else ""
    badge_html += f'<span class="jm-badge">{SOURCE_LABEL.get(job.get("source"), job.get("source") or "")}</span>'
    return (f'<div class="jm-card" style="--accent:{accent}">{top}{head}{stage}{chips}{text}'
            f'<div class="jm-row">{badge_html}</div>{details(job)}</div>')


def details(job):
    ai = job.get("ai") or {}
    if not ai:
        return ""
    meta = "".join(f"<div><dt>{k}</dt><dd>{escape(str(v or '—'))}</dd></div>" for k, v in [
        ("Level", ai.get("level")), ("Level band", C.LEVEL_LABEL.get(ai.get("levelBand"), "")),
        ("Working language", ai.get("workingLanguage")), ("Discipline fit", ai.get("disciplineFit")),
        ("Fit role", ai.get("fitRole")), ("Evidence", ai.get("evidence"))])
    blockers = "".join(f'<li><b>{"Screens him out" if b["kind"] == "screen" else "Arguable"}:</b> {escape(b["text"])}</li>'
                       for b in ai.get("blockers", []))
    body = (f'<dl class="jm-meta">{meta}</dl>' +
            (f'<div class="jm-list" style="--c:var(--jm-mismatch)"><h4>Blockers</h4><ul>{blockers}</ul></div>' if blockers else "") +
            _list("Strong", ai.get("strong"), "var(--jm-strong)") + _list("Reframeable", ai.get("reframeable"), "var(--jm-adjacent)") +
            _list("Gaps", ai.get("gaps"), "var(--jm-mismatch)") + _tags("Signature projects", ai.get("signatureProjects")) +
            _tags("Key skills", ai.get("keySkills")) + _tags("Tools", ai.get("tools")))
    return f'<details class="jm-more"><summary>Full analysis</summary>{body}</details>'


def board(jobs):
    if not jobs:
        return '<div class="jm-empty">No jobs match these filters.</div>'
    return '<div class="jm-grid">' + "".join(card(j) for j in jobs) + "</div>"


def how_scored(result):
    """The RAG trace behind one assessment: requirements, evidence, examples, guardrails."""
    if result["source"] != "rag+llm":
        return f'<div class="jm-panel"><b>Offline keyword score.</b> <span class="jm-note">{escape(result.get("error") or "")}</span></div>'
    a = result["assessment"]
    verdict = {m["requirement_id"]: m for m in a.get("requirement_matches", [])}
    reqs = "".join(
        f'<tr><td>{r["id"]}</td><td>{escape(r["ask"])}<div class="jm-note">{r["importance"]} · {r["pillar"]}</div></td>'
        f'<td>{verdict.get(r["id"], {}).get("verdict", "—")}</td><td class="jm-cite">{", ".join(verdict.get(r["id"], {}).get("evidence_ids", []))}</td>'
        f'<td>{escape(verdict.get(r["id"], {}).get("note", ""))}</td></tr>' for r in result["posting"]["requirements"])
    ev = "".join(f'<tr><td class="jm-cite">{e["eid"]}</td><td>{escape(e["doc_title"])}<div class="jm-note">{escape(e["section"] or "main")}</div></td>'
                 f'<td>{", ".join(e["supports"])}</td><td>{e["score"]}</td><td>{escape(e["text"][:220])}…</td></tr>' for e in result["evidence"])
    ex = "".join(f'<tr><td>{escape(e["title"])} · {escape(e["company"])}</td><td>{e["fit"]} / {e["win"]}</td>'
                 f'<td>{escape(e["outcome"])}</td><td>{e["similarity"]}</td></tr>' for e in result["examples"])
    notes = "".join(f"<li>{escape(n)}</li>" for n in result["guardrails"]) or "<li>No adjustments needed.</li>"
    t = result["timings"]
    return (f'<div class="jm-panel"><div class="jm-h4">Requirements and verdicts</div><table class="jm-table"><tr><th>#</th><th>Requirement</th>'
            f'<th>Verdict</th><th>Evidence</th><th>Note</th></tr>{reqs}</table>'
            f'<div class="jm-h4" style="margin-top:12px">Evidence pack (reranker: {result["reranker"]})</div><table class="jm-table"><tr><th>Id</th>'
            f'<th>Source</th><th>For</th><th>Score</th><th>Excerpt</th></tr>{ev}</table>'
            f'<div class="jm-h4" style="margin-top:12px">Calibration examples (few-shot, nearest past roles)</div><table class="jm-table"><tr>'
            f'<th>Role</th><th>Fit / Win then</th><th>What happened</th><th>Similarity</th></tr>{ex}</table>'
            f'<div class="jm-h4" style="margin-top:12px">Guardrails</div><ul class="jm-p">{notes}</ul>'
            f'<p class="jm-note">Timings: {", ".join(f"{k} {v}s" for k, v in t.items())}</p></div>')


def kpis(items):
    return '<div class="jm-kpis">' + "".join(f'<div class="jm-kpi"><div class="v">{v}</div><div class="l">{escape(l)}</div></div>'
                                             for l, v in items) + "</div>"


def linkedin_links(mode, company, recency, location="Berlin, Germany"):
    common = (f"&location={quote(location)}" + ("&geoId=106967730" if "berlin" in location.lower() else "") +
              "&sortBy=DD" + (f"&f_TPR={C.RECENCY[recency]}" if recency in C.RECENCY else ""))
    base = "https://www.linkedin.com/jobs/search/?"
    keyword = lambda name: base + "keywords=" + quote(f'("{name}") AND {C.SEARCH_TERMS}') + common
    tier_key = {"Tier 1": "t1", "Tier 2": "t2", "Tier 3": "t3", "Expansion": "t4"}.get(mode)
    links = []
    if tier_key:
        names = C.TIERS[tier_key]
        ids = [C.COMPANIES[n] for n in names if C.COMPANIES.get(n)]
        links.append((f"{mode}: {len(ids)} companies in one search", base + "f_C=" + ",".join(ids) + common) if ids else None)
        links += [(f"{n} (keyword search)", keyword(n)) for n in names if not C.COMPANIES.get(n)]
    elif mode == "All companies":
        links.append(("Open search on your skill terms", base + "keywords=" + quote(C.SEARCH_TERMS) + common))
    else:
        name = (company or "").strip()
        if not name:
            return '<p class="jm-note">Type a company name first.</p>'
        cid = next((v for k, v in C.COMPANIES.items() if k.lower() == name.lower()), None)
        links.append((f"{name} jobs", base + f"f_C={cid}" + common) if cid else (f"{name} + your skill terms", keyword(name)))
    html = "".join(f'<a href="{escape(u)}" target="_blank" rel="noopener">{escape(t)} ↗</a>' for t, u in filter(None, links))
    return f'<div class="jm-links">{html}</div><p class="jm-note">Berlin, newest first. Sign in to LinkedIn for the filters to hold.</p>'
