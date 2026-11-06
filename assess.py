"""Job assessment pipeline.

  1. decompose  - LLM turns the posting into facts + 4-7 prioritised requirements, each with a
                  HyDE-style evidence query (what proof in a CV would look like)
  2. retrieve   - multi-query hybrid search + rerank per requirement -> [E#] evidence pack
  3. calibrate  - dynamic few-shot: the 3 most similar past assessments WITH their real outcomes
  4. assess     - rubric prompt -> Structured Output whose field order forces evidence before scores
  5. guard      - deterministic rubric caps, citation validation, sanitising
Falls back to the artifact's offline keyword scorer when no LLM is available.
"""
import json
import re
import time
from functools import lru_cache
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

import candidate as C
import config
import llm
import rag
import scoring


# ---------- structured output schemas ----------
class Requirement(BaseModel):
    id: str = Field(description="R1, R2, ... most important first")
    ask: str = Field(description="the requirement in one short sentence")
    pillar: Literal["P1", "P2", "P3", "P4", "P5", "Domain"]
    importance: Literal["critical", "important", "nice-to-have"]
    evidence_query: str = Field(description="the proof a strong CV would contain, phrased like a CV line")


class Posting(BaseModel):
    title: str
    company: str
    location: str
    level: str = Field(description="seniority in the posting's own words")
    working_language: str
    german_required: bool = Field(description="true only if fluent, business, C1/C2 or native German is required")
    requirements: list[Requirement]
    screens: list[str]


class Match(BaseModel):
    requirement_id: str
    verdict: Literal["direct", "adjacent", "argued", "missing"]
    evidence_ids: list[str]
    note: str


class Point(BaseModel):
    text: str
    evidence_ids: list[str]


class Blocker(BaseModel):
    text: str
    kind: Literal["screen", "argue"]


class Assessment(BaseModel):  # field order = generation order: evidence first, numbers last
    title: str
    company: str
    location: str
    level: str
    levelBand: Literal["below", "senior-mgr", "head", "director", "senior-ic", "vp", "unclear"]
    workingLanguage: str
    germanRequired: bool
    germanLanguagePost: bool
    roleType: str
    requirement_matches: list[Match]
    strong: list[Point]
    reframeable: list[Point]
    gaps: list[str]
    blockers: list[Blocker]
    evidence: Literal["direct", "adjacent", "argued"]
    disciplineFit: Literal["strong", "adjacent", "mismatch"]
    pillar: str
    fitRole: str
    signatureProjects: list[str]
    keySkills: list[str]
    tools: list[str]
    postedDate: str
    fit: int = Field(description="0-100, computed from the lists above")
    win: int = Field(description="0-100, standing against the likely shortlist")
    winWhy: str
    recommendation: str = Field(description="one sentence: pursue, stretch or skip, and why")


# ---------- helpers ----------
def job_id(title, company):
    """Same id scheme as the Claude artifact, so a re-pasted job is recognised."""
    h = 0
    for ch in f"{title}|{company}":
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    digits, out = "0123456789abcdefghijklmnopqrstuvwxyz", ""
    while True:
        h, r = divmod(h, 36)
        out = digits[r] + out
        if not h:
            return "j" + out


def split_postings(text):
    parts = [p.strip() for p in re.split(r"\n\s*(?:-{3,}|={3,})\s*\n", text) if p.strip()]
    return parts or [text]


def guess_header(text):
    """Title / company / location for the offline path (artifact heuristics)."""
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
    title, company, location = (lines[0] if lines else "Untitled role")[:120], "", ""
    for ln in lines[1:10]:
        if not location and re.search(r"berlin|remote|hybrid|germany|deutschland|münchen|munich|hamburg", ln, re.I):
            location = ln[:80]
        m = re.match(r"^([A-Za-zÄÖÜäöüß0-9 .&'-]{2,45})\s*·", ln)
        if not company and m:
            company = m.group(1).strip()
    return title, company or "Unknown", location


def outcome(job):
    status, sub, furthest = job.get("status"), job.get("subStatus"), job.get("furthest")
    if status == "dismissed":
        return f"not pursued (reason: {C.SUBSTATUS_LABEL.get(sub, 'not recorded').lower()})"
    reached = C.STAGES[furthest][1].lower() if isinstance(furthest, int) and 0 <= furthest < len(C.STAGES) else ""
    if sub == "rejected":
        return f"applied, rejected after reaching {reached}" if furthest and furthest > 1 else \
            "applied, rejected at the application stage" if furthest == 1 else "applied, rejected (stage reached not recorded)"
    return f"still live, at {C.SUBSTATUS_LABEL.get(sub, sub or 'unknown stage').lower()}"


@lru_cache(None)
def history():
    jobs = json.loads(config.HISTORY_PATH.read_text()) if config.HISTORY_PATH.exists() else []
    return [j for j in jobs if (j.get("ai") or {}).get("win") is not None]  # examples need both numbers


@lru_cache(None)
def _history_vectors():
    texts = [f"{j['title']} at {j['company']}. {j['ai'].get('roleType', '')}. {', '.join(j['ai'].get('keySkills', [])[:8])}"
             for j in history()]
    return rag.embed(texts) if texts else np.zeros((0, 1))


def _same_role(job, posting):
    a, b = set(re.findall(r"\w+", job["title"].lower())), set(re.findall(r"\w+", posting.title.lower()))
    same_company = (job["company"].lower().split() or ["?"])[0] == (posting.company.lower().split() or [""])[0]
    return same_company and len(a & b) / max(1, len(a | b)) >= 0.5


def pick_examples(posting, k=3, leave_out_same_role=True):
    jobs = history()
    if not jobs:
        return []
    query = rag.embed([f"{posting.title} at {posting.company}. " + "; ".join(r.ask for r in posting.requirements)])[0]
    sims = _history_vectors() @ query
    picked = []
    for i in np.argsort(-sims):
        j = jobs[i]
        if leave_out_same_role and _same_role(j, posting):
            continue  # never show the model its own earlier verdict on this very role
        a = j["ai"]
        picked.append({"title": j["title"], "company": j["company"], "fit": a.get("score"), "win": a.get("win"),
                       "evidence": a.get("evidence", ""), "levelBand": a.get("levelBand", ""),
                       "blockers": [f"{b['text']} ({b['kind']})" for b in a.get("blockers", [])][:3],
                       "winWhy": a.get("winWhy", ""), "outcome": outcome(j), "similarity": round(float(sims[i]), 3)})
        if len(picked) == k:
            return picked
    return picked


def format_examples(examples):
    out = []
    for n, e in enumerate(examples, 1):
        out.append(f"[Example {n}] {e['title']} at {e['company']} (level band {e['levelBand'] or 'n/a'})\n"
                   f"  Scored then: fit {e['fit']}, win {e['win']}, evidence {e['evidence'] or 'n/a'}. "
                   f"Blockers: {'; '.join(e['blockers']) or 'none listed'}\n"
                   f"  Who beats him: {e['winWhy'] or 'n/a'}\n"
                   f"  What actually happened: {e['outcome']}")
    return "\n".join(out)


def build_messages(job_text, posting, pack, examples):
    system = ("You are a senior executive headhunter assessing a job for this candidate.\n\n"
              f"{C.PROFILE}\n\n{C.OUTCOME_CALIBRATION}\n\n{C.RUBRIC}")
    reqs = "\n".join(f"{r.id} [{r.importance}, {r.pillar}] {r.ask}" for r in posting.requirements)
    evidence = "\n\n".join(f"[{e['eid']}] {e['doc_title']} › {e['section'] or 'main'} (retrieved for {', '.join(e['supports'])})\n{e['text']}"
                           for e in pack) or "(no evidence retrieved)"
    user = (f"CALIBRATION EXAMPLES: real past assessments of the most similar roles, and what actually happened. "
            f"Use them to calibrate your numbers against outcomes; the posting below is a different role.\n{format_examples(examples)}\n\n"
            f"REQUIREMENTS decomposed from the posting, most important first:\n{reqs}\n"
            f"Screens flagged in the posting: {'; '.join(posting.screens) or 'none'}\n\n"
            f"EVIDENCE PACK retrieved from his own documents (cite by id):\n{evidence}\n\n"
            f'JOB TEXT:\n"""\n{job_text[:18000]}\n"""')
    return system, user


def decompose(job_text):
    return llm.parse(config.LLM_MODEL_FAST, C.DECOMPOSE_PROMPT, job_text[:18000], Posting, effort="low")


# ---------- the pipeline ----------
def assess(job_text, use_llm=True, leave_out_same_role=True):
    t0, timings = time.time(), {}
    if not (use_llm and llm.available()):
        return offline(job_text, "No OpenAI key configured." if use_llm else "LLM disabled for this run.")
    try:
        posting = decompose(job_text)
        timings["decompose"] = round(time.time() - t0, 1)
        t = time.time()
        pack = rag.get().evidence_pack([r.model_dump() for r in posting.requirements])
        examples = pick_examples(posting, leave_out_same_role=leave_out_same_role)
        timings["retrieve+examples"] = round(time.time() - t, 1)
        system, user = build_messages(job_text, posting, pack, examples)
        t = time.time()
        raw = llm.parse(config.LLM_MODEL, system, user, Assessment, effort=config.REASONING_EFFORT).model_dump()
        timings["assess"] = round(time.time() - t, 1)
    except Exception as e:  # network, quota, parsing: keep the board usable
        return offline(job_text, f"LLM path failed ({type(e).__name__}: {str(e)[:160]}).")
    a, notes = scoring.guard(json.loads(json.dumps(raw)), {e["eid"] for e in pack})
    a = scoring.sanitize(a)
    timings["total"] = round(time.time() - t0, 1)
    return {"id": job_id(a["title"], a["company"]), "source": "rag+llm", "assessment": a, "raw": raw,
            "posting": posting.model_dump(), "evidence": pack, "examples": examples, "guardrails": notes,
            "reranker": rag.get().reranker, "prompt": {"system": system, "user": user}, "timings": timings, "error": None}


def offline(job_text, reason):
    title, company, location = guess_header(job_text)
    a = scoring.offline_score(title, company, location, job_text)
    return {"id": job_id(title, company), "source": "offline", "assessment": a, "raw": None, "posting": None,
            "evidence": [], "examples": [], "guardrails": [], "reranker": None, "prompt": None, "timings": {},
            "error": reason}


def _cite(p):
    return f"{p['text']} [{', '.join(p['evidence_ids'])}]" if p.get("evidence_ids") else p["text"]


def to_board(result, job_text):
    """Assessment -> the job record shape shared by the artifact and the Lovable app."""
    a = result["assessment"]
    ai = {"score": a["fit"], "win": a["win"], "winWhy": a["winWhy"], "summary": a["recommendation"], "level": a["level"],
          "levelBand": a["levelBand"], "workingLanguage": a["workingLanguage"], "germanRequired": a["germanRequired"],
          "germanPost": a["germanLanguagePost"], "roleType": a["roleType"], "disciplineFit": a["disciplineFit"],
          "pillar": a["pillar"], "fitRole": a["fitRole"], "postedDate": a["postedDate"],
          "signatureProjects": a["signatureProjects"], "keySkills": a["keySkills"], "tools": a["tools"],
          "strong": [_cite(p) for p in a["strong"]], "reframeable": [_cite(p) for p in a["reframeable"]],
          "gaps": a["gaps"], "blockers": a["blockers"], "evidence": a["evidence"],
          "rag": {"source": result["source"], "requirements": (result["posting"] or {}).get("requirements", []),
                  "matches": a.get("requirement_matches", []), "guardrails": result["guardrails"],
                  "evidence": [{k: e[k] for k in ("eid", "doc_title", "section", "supports", "score", "text")} for e in result["evidence"]],
                  "error": result["error"]}}
    return {"id": result["id"], "title": a["title"], "company": a["company"], "location": a["location"],
            "fit": a["fit"], "win": a["win"], "description": job_text, "ai": ai, "source": result["source"]}
