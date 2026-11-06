"""Job Match Studio: the Lovable app's board and layout, the Claude artifact's Fit/Win
scoring, and a RAG layer over the Google Drive project folder. Run: python app.py"""
import json
import statistics
import threading

import gradio as gr
import pandas as pd

import assess
import candidate as C
import config
import drive_sync
import ingest
import llm
import materials
import rag
import store
import ui
from scoring import company_tier

TIERS = ["Any tier"] + [C.TIER_LABEL[k] for k in ("t1", "t2", "t3", "t4", "other")]
OUTCOME_COLORS = {"In process": "#2a78d6", "Rejected": "#eb6834", "Not pursued": "#1baf7a"}  # colour-blind-safe trio
SHORT_STAGE = {"Recruiter screen": "Screen", "Hiring manager": "Hiring mgr", "Assignment / case": "Assignment",
               "Panel / final": "Final round"}
STAGE_ORDER = ["Applied"] + [SHORT_STAGE.get(label, label) for _, label in C.STAGES[2:]]


# ---------- board ----------
def filtered(status="All", tier="Any tier", min_fit=0, sort="Fit"):
    jobs = store.jobs()
    if status != "All":
        jobs = [j for j in jobs if j["status"] == status.lower()]
    if tier != "Any tier":
        jobs = [j for j in jobs if C.TIER_LABEL[company_tier(j["company"])] == tier]
    jobs = [j for j in jobs if (j["fit"] or 0) >= (min_fit or 0)]
    key = "win" if sort == "Win" else "fit"
    return sorted(jobs, key=lambda j: -(j[key] if j[key] is not None else -1))


def table(jobs):
    return pd.DataFrame([{"Fit": j["fit"], "Win": j["win"], "Role": j["title"], "Company": j["company"],
                          "Status": j["status"], "Stage": C.SUBSTATUS_LABEL.get(j["sub_status"], ""),
                          "Pillar": j["ai"].get("pillar", ""), "Evidence": j["ai"].get("evidence", ""),
                          "Source": ui.SOURCE_LABEL.get(j["source"], j["source"])} for j in jobs],
                        columns=["Fit", "Win", "Role", "Company", "Status", "Stage", "Pillar", "Evidence", "Source"])


def job_choices():
    return [(f"{j['title']} · {j['company']}", j["id"]) for j in store.jobs()]


def refresh(status, tier, min_fit, sort):
    jobs, everything = filtered(status, tier, min_fit, sort), store.jobs()
    counts = " · ".join(f"{s} {sum(j['status'] == s.lower() for j in everything) if s != 'All' else len(everything)}"
                        for s in ("All", "New", "Saved", "Dismissed"))
    return ui.board(jobs), table(jobs), f"**{len(jobs)} shown** · {counts}", gr.update(choices=job_choices())


def score(text, split, status, tier, min_fit, sort):
    if not (text or "").strip():
        raise gr.Error("Paste a job posting first.")
    if text.strip().startswith("http") and len(text.split()) < 4:
        raise gr.Error("LinkedIn blocks automated access to job pages. Open the job, copy the page text and paste that.")
    results = []
    ids = []
    for part in (assess.split_postings(text) if split else [text]):
        result = assess.assess(part)
        ids.append(store.upsert(assess.to_board(result, part)))
        results.append(result)
    if results[-1]["source"] == "offline":
        gr.Warning(f"Scored offline: {results[-1]['error']}")
    scored = ui.board([store.get(i) for i in ids])
    return (scored, ui.how_scored(results[-1]), *refresh(status, tier, min_fit, sort))


def set_view(view):
    return gr.update(visible=view == "Cards"), gr.update(visible=view == "Table")


def substatus_options(status):
    return gr.update(choices=[(label, key) for key, label in C.SUBSTATUS[status]], value=None)


def update_job(job_id, status, sub, *filters):
    if not job_id:
        raise gr.Error("Pick a job first.")
    store.set_status(job_id, status, sub)
    return refresh(*filters)


def delete_job(job_id, *filters):
    if job_id:
        store.delete(job_id)
    return refresh(*filters)


# ---------- analysis ----------
def outcome_group(j):
    return "Not pursued" if j["status"] == "dismissed" else "Rejected" if j["sub_status"] == "rejected" else "In process"


def analysis():
    jobs = store.jobs()
    rows, unknown = store.funnel()
    applied = [j for j in jobs if j["status"] == "saved"]
    funnel = dict(rows)
    med = lambda xs: round(statistics.median(xs)) if xs else "—"
    tiles = ui.kpis([("Jobs on the board", len(jobs)), ("Applications", funnel["Applied"]),
                     ("Reached a recruiter screen", funnel["Recruiter screen"]), ("Reached hiring manager", funnel["Hiring manager"]),
                     ("Final rounds", funnel["Panel / final"]), ("Offers", funnel["Offer"]),
                     ("Median Fit, applications", med([j["fit"] for j in applied if j["fit"] is not None])),
                     ("Median Win, applications", med([j["win"] for j in applied if j["win"] is not None]))])
    note = (f"{unknown} applications concluded before stages were tracked, so they count only as Applied. "
            "Win is blank for entries scored before Win existed.")
    scatter = pd.DataFrame([{"Fit": j["fit"], "Win": j["win"], "Outcome": outcome_group(j), "Role": j["title"],
                             "Company": j["company"]} for j in jobs if j["fit"] is not None and j["win"] is not None])
    funnel_df = pd.DataFrame([(SHORT_STAGE.get(stage, stage), n) for stage, n in rows], columns=["Stage", "Applications"])
    return tiles, funnel_df, scatter, note, table(sorted(jobs, key=lambda j: -(j["fit"] or 0)))


# ---------- application materials ----------
def material_choices():
    return [(f"{j['fit']}/{j['win'] if j['win'] is not None else '–'} · {j['title']} · {j['company']}", j["id"])
            for j in filtered(sort="Fit") if (j.get("description") or "").strip()]


def draft(job_id, pasted):
    try:
        if (pasted or "").strip():
            job = store.get(store.upsert(assess.to_board(assess.assess(pasted), pasted)))
        elif job_id:
            job = store.get(job_id)
        else:
            raise gr.Error("Pick a scored job or paste a posting.")
        out = materials.generate(job)
    except RuntimeError as e:
        raise gr.Error(str(e))
    rows = "".join(f'<tr><td>{"✓" if c["pass"] else "✗"}</td><td>{c["check"]}</td><td>{c["detail"]}</td></tr>' for c in out["checks"])
    passed = sum(c["pass"] for c in out["checks"])
    checks = (f'<div class="jm-panel"><div class="jm-h4">Drafting checks: {passed}/{len(out["checks"])} passed · '
              f'style example: {out["style_example"]} · {out["evidence_used"]} evidence chunks</div>'
              f'<table class="jm-table"><tr><th></th><th>Check</th><th>Detail</th></tr>{rows}</table>'
              f'<p class="jm-note">Notes: {" ".join(out["materials"]["notes"])}</p></div>')
    return (out["materials"]["coverLetter"], "```text\n" + materials.plain_cv(out["materials"]) + "\n```", checks,
            out["files"], gr.update(choices=material_choices()))


# ---------- knowledge base ----------
def kb_overview():
    if not config.CHUNKS_PATH.exists():
        return '<div class="jm-panel">No index yet. Press "Rebuild index".</div>', pd.DataFrame()
    chunks = [json.loads(line) for line in config.CHUNKS_PATH.open(encoding="utf-8")]
    per_doc = pd.DataFrame(chunks).groupby(["doc_title", "doc_type", "folder", "modified"]).agg(
        chunks=("id", "count"), tokens=("tokens", "sum")).reset_index().sort_values("doc_type")
    per_doc.columns = ["Document", "Type", "Drive folder", "Modified", "Chunks", "Tokens"]
    manifest = json.loads((config.DRIVE_DIR / "manifest.json").read_text()) if (config.DRIVE_DIR / "manifest.json").exists() else []
    source = {m.get("source") for m in manifest} or {"local files"}
    stats = ui.kpis([("Documents", len(per_doc)), ("Chunks", len(chunks)), ("Tokens indexed", f"{per_doc.Tokens.sum():,}"),
                     ("Embeddings", config.EMBED_MODEL.split("/")[-1]), ("Reranker", rag.reranker_name()),
                     ("LLM", config.LLM_MODEL if llm.available() else "offline (no key)")])
    return stats + f'<p class="jm-note">Drive mirror source: {", ".join(sorted(source))}. Folder id {config.DRIVE_FOLDER_ID}.</p>', per_doc


def kb_rebuild():
    report = ingest.run()
    gr.Info(f"Indexed {report['chunks']} chunks from {len(report['docs'])} documents.")
    return kb_overview()


def kb_sync():
    try:
        files = drive_sync.sync()
    except FileNotFoundError as e:
        raise gr.Error(str(e))
    gr.Info(f"Mirrored {len(files)} files from Google Drive.")
    return kb_rebuild()


def kb_search(query, mode):
    if not (query or "").strip():
        raise gr.Error("Type a query.")
    trace = {}
    hits = rag.get().search(query, k=6, mode=mode, trace=trace)
    results = pd.DataFrame([{"Rank": i + 1, "Score": h["score"], "Document": h["doc_title"], "Section": h["section"] or h["subsection"],
                             "Projects": h["projects"].replace("|", ", "), "Excerpt": h["text"][:300]} for i, h in enumerate(hits)])
    label = lambda cid: rag.get().by_id[cid]["doc_title"][:28] + " · " + cid.rsplit("-", 1)[-1]
    stages = {name: [label(cid) for cid, _ in trace.get(name, [])[:6]] for name in ("dense", "bm25", "fused", "reranked")}
    depth = max(len(v) for v in stages.values())
    stages_df = pd.DataFrame({k.title(): v + [""] * (depth - len(v)) for k, v in stages.items()})
    return results, stages_df


# ---------- layout ----------
def build():
    threading.Thread(target=lambda: rag.embed(["warm-up"]), daemon=True).start()  # load the embedding model early
    store.init()
    if not store.jobs():
        store.import_history()
    filters_defaults = ("All", "Any tier", 0, "Fit")
    with gr.Blocks(title="Job Match Studio") as demo:
        gr.HTML(ui.header())
        with gr.Tabs():
            with gr.Tab("Board"):
                with gr.Row(equal_height=True):
                    with gr.Column(variant="panel"):
                        gr.Markdown("**Launch a LinkedIn search**  \nBerlin, newest first.")
                        mode = gr.Dropdown(["Tier 1", "Tier 2", "Tier 3", "Expansion", "All companies", "Single company"],
                                           value="Tier 1", label="Companies")
                        company = gr.Textbox(label="Company (single company mode)", placeholder="e.g. Contentful")
                        recency = gr.Dropdown(list(C.RECENCY), value="Last week", label="Posted within")
                        launch = gr.Button("Build LinkedIn search", variant="primary")
                        links = gr.HTML()
                    with gr.Column(variant="panel", scale=2):
                        gr.Markdown("**Paste results to score**  \nScored against your Drive portfolio with RAG. "
                                    "Falls back to offline keyword scoring if the LLM is unavailable.")
                        paste = gr.Textbox(lines=10, show_label=False,
                                           placeholder="Paste a copied job posting. For several, separate them with a line of ---")
                        with gr.Row():
                            split = gr.Checkbox(label="Split: treat as multiple postings (separated by ---)")
                            score_btn = gr.Button("Score & add", variant="primary")
                scored = gr.HTML()
                with gr.Accordion("How this score was built", open=False):
                    trace = gr.HTML()
                with gr.Row():
                    status_f = gr.Radio(["All", "New", "Saved", "Dismissed"], value="All", label="Status")
                    tier_f = gr.Dropdown(TIERS, value="Any tier", label="Tier")
                    fit_f = gr.Slider(0, 100, value=0, step=5, label="Minimum Fit")
                    sort_f = gr.Radio(["Fit", "Win"], value="Fit", label="Sort by")
                    view_f = gr.Radio(["Cards", "Table"], value="Cards", label="View")
                counts = gr.Markdown()
                board_html = gr.HTML()
                board_df = gr.Dataframe(visible=False, interactive=False, wrap=True)
                with gr.Accordion("Update or delete a job", open=False):
                    with gr.Row():
                        job_dd = gr.Dropdown(label="Job", choices=job_choices())
                        status_dd = gr.Dropdown(["new", "saved", "dismissed"], value="saved", label="Status")
                        sub_dd = gr.Dropdown([(label, key) for key, label in C.SUBSTATUS["saved"]], label="Stage or reason")
                    with gr.Row():
                        update_btn = gr.Button("Update", variant="primary")
                        delete_btn = gr.Button("Delete", variant="stop")

            with gr.Tab("Analysis"):
                tiles = gr.HTML()
                with gr.Row():
                    funnel_plot = gr.BarPlot(x="Stage", y="Applications", sort=STAGE_ORDER, title="Applications by furthest stage reached",
                                             tooltip=["Stage", "Applications"], height=320)
                    scatter_plot = gr.ScatterPlot(x="Fit", y="Win", color="Outcome", color_map=OUTCOME_COLORS, x_lim=[0, 100],
                                                  y_lim=[0, 100], title="Fit against Win, by outcome",
                                                  tooltip=["Role", "Company", "Fit", "Win", "Outcome"], height=320)
                analysis_note = gr.Markdown()
                with gr.Accordion("Table view", open=False):
                    analysis_df = gr.Dataframe(interactive=False, wrap=True)
                refresh_analysis = gr.Button("Refresh")

            with gr.Tab("Application Materials"):
                gr.Markdown("Drafts a cover letter and CV grounded in your canonical record and the job's evidence pack, "
                            "styled on your closest past cover letter, then checks them against your drafting rules.")
                with gr.Row():
                    job_pick = gr.Dropdown(material_choices(), label="Scored job (with posting text)")
                    pasted = gr.Textbox(lines=3, label="…or paste a new posting")
                draft_btn = gr.Button("Draft cover letter and CV", variant="primary")
                checks = gr.HTML()
                with gr.Row():
                    letter = gr.Textbox(label="Cover letter", lines=18, buttons=["copy"])
                    cv = gr.Markdown(label="CV")
                files = gr.File(label="Downloads (.docx and .md)", file_count="multiple")

            with gr.Tab("Knowledge Base"):
                kb_stats = gr.HTML()
                kb_docs = gr.Dataframe(interactive=False, wrap=True, label="Indexed documents")
                with gr.Row():
                    sync_btn = gr.Button("Sync from Google Drive")
                    rebuild_btn = gr.Button("Rebuild index")
                gr.Markdown("**Retrieval playground**: see every stage of the search for any query.")
                with gr.Row():
                    query = gr.Textbox(label="Query", placeholder="e.g. influencing partner teams without authority", scale=3)
                    search_mode = gr.Radio(["dense", "bm25", "hybrid", "hybrid+rerank"], value="hybrid+rerank", label="Mode")
                search_btn = gr.Button("Search", variant="primary")
                hits = gr.Dataframe(interactive=False, wrap=True, label="Results")
                stages = gr.Dataframe(interactive=False, wrap=True, label="Top hits at each stage")

        filters = [status_f, tier_f, fit_f, sort_f]
        board_out = [board_html, board_df, counts, job_dd]
        launch.click(ui.linkedin_links, [mode, company, recency], links, api_name="linkedin")
        score_btn.click(score, [paste, split] + filters, [scored, trace] + board_out, api_name="score")
        for f in filters:
            f.change(refresh, filters, board_out, api_name=False)
        view_f.change(set_view, view_f, [board_html, board_df], api_name=False)
        status_dd.change(substatus_options, status_dd, sub_dd, api_name=False)
        update_btn.click(update_job, [job_dd, status_dd, sub_dd] + filters, board_out, api_name="update_job")
        delete_btn.click(delete_job, [job_dd] + filters, board_out, api_name=False)
        refresh_analysis.click(analysis, None, [tiles, funnel_plot, scatter_plot, analysis_note, analysis_df], api_name="analysis")
        draft_btn.click(draft, [job_pick, pasted], [letter, cv, checks, files, job_pick], api_name="draft")
        sync_btn.click(kb_sync, None, [kb_stats, kb_docs], api_name=False)
        rebuild_btn.click(kb_rebuild, None, [kb_stats, kb_docs], api_name="rebuild_index")
        search_btn.click(kb_search, [query, search_mode], [hits, stages], api_name="kb_search")
        demo.load(lambda: refresh(*filters_defaults), None, board_out, api_name=False)
        demo.load(analysis, None, [tiles, funnel_plot, scatter_plot, analysis_note, analysis_df], api_name=False)
        demo.load(kb_overview, None, [kb_stats, kb_docs], api_name=False)
    return demo


if __name__ == "__main__":
    build().launch(theme=ui.theme(), css=ui.CSS, allowed_paths=[str(config.EXPORTS_DIR)])
