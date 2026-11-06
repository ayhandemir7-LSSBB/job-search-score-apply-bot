"""Application materials (the Lovable app's third tab), rebuilt on the RAG layer.

Grounding: canonical record (outranks everything) + the job's evidence pack.
Style few-shot: the most similar of his own past cover letters, retrieved by a
metadata-filtered search. Every draft is checked against the drafting rules.
"""
import json
import re

from pydantic import BaseModel

import assess
import candidate as C
import config
import llm
import rag


class CvEntry(BaseModel):
    role: str
    org: str
    location: str
    dates: str
    bullets: list[str]


class Cv(BaseModel):
    name: str
    headline: str
    contact: str
    summary: str
    experience: list[CvEntry]
    education: list[CvEntry]
    skills: list[str]
    certifications: list[str]
    awards: list[str]


class Materials(BaseModel):
    coverLetter: str
    cv: Cv
    notes: list[str]


BANNED = ["passionate about", "team player", "responsible for", "the only", "unparalleled"]
EXCLUDED = re.compile("|".join(C.EXCLUDED_CLAIMS), re.I)
OPPORTUNITY = re.compile(r"2\.1\s?B|2\.1 billion|\$8\s?B|8 billion", re.I)
DELIVERY_VERBS = re.compile(r"\b(secured|delivered|generated|reali[sz]ed|captured|saved|achieved|unlocked|drove)\b", re.I)
VP_WELLBEING = re.compile(r"\bVP\b[^.]{0,80}(wellbeing|mental health|affinity)|(wellbeing|mental health|affinity)[^.]{0,80}\bVP\b", re.I)
FIGURE_OWNERS = {  # a sentence quoting the figure must also name its project
    r"93\.5\s?%": r"auditai|audit", r"\b80\s?%": r"buwg|back-up work group|kaizen", r"\$?132\s?M\b": r"concession|access|permission",
    r"\$?85\s?M\b": r"fraud|mail label|return", r"2\.1\s?B|2\.1 billion": r"packing|ixd|opportunit|gap", r"\b70\s?%": r"audit",
    r"\$?15\s?MM\b": r"pls|product life support|programme|program"}


def analysis_text(job):
    ai = job.get("ai") or {}
    reqs = "\n".join(f"{r['id']} {r['ask']}" for r in (ai.get("rag") or {}).get("requirements", []))
    return (f"Role: {job['title']} at {job['company']} ({job.get('location', '')}). Fit {job.get('fit')}, win {job.get('win')}.\n"
            f"Pillar: {ai.get('pillar', '')}. Fit role: {ai.get('fitRole', '')}. Level: {ai.get('level', '')}.\n"
            f"Requirements:\n{reqs or '(not decomposed)'}\nStrong: {'; '.join(ai.get('strong', []))}\n"
            f"Reframeable: {'; '.join(ai.get('reframeable', []))}\nGaps: {'; '.join(ai.get('gaps', []))}\n"
            f"Recommendation: {ai.get('summary', '')}")


def evidence_for(job):
    pack = ((job.get("ai") or {}).get("rag") or {}).get("evidence")
    if pack:
        return pack
    posting = assess.decompose(job["description"])  # history entries were never decomposed
    return rag.get().evidence_pack([r.model_dump() for r in posting.requirements])


def build_messages(job, pack, style_title, style_text):
    system = ("You draft job application materials for Ayhan Demir. Output a FIRST DRAFT: structure and factual "
              f"grounding matter more than polish.\n\nPRIMARY SOURCE OF TRUTH:\n\"\"\"\n{C.CANONICAL_FACTS}\n\"\"\"\n\n{C.MATERIALS_RULES}")
    evidence = "\n\n".join(f"[{e['eid']}] {e['doc_title']} › {e['section'] or 'main'}\n{e['text']}" for e in pack)
    user = (f"SUPPORTING EVIDENCE from his own documents (narrative and phrasing; the primary record wins any conflict):\n{evidence}\n\n"
            f"TARGET JOB ANALYSIS:\n{analysis_text(job)}\n\n"
            f"STYLE EXAMPLE, one of his own past cover letters ({style_title}). Mirror its voice, rhythm and structure. "
            f"Do not reuse its company-specific sentences, and take facts only from the sources above:\n\"\"\"\n{style_text}\n\"\"\"\n\n"
            f"JOB POSTING:\n\"\"\"\n{(job.get('description') or '')[:12000]}\n\"\"\"\n\n"
            "Write the cover letter (paragraphs separated by blank lines) and the CV. In notes, give first the employer-selection "
            "decision and why, then anything a stronger application would need that is not in the sources.")
    return system, user


def fix_dashes(s):
    s = re.sub(r"(\b\d{4})\s*[–—]\s*(\d{4}|[Pp]resent)\b", r"\1 to \2", s)
    return re.sub(r"\s*[—–]\s*", ", ", s)


def _walk(obj, fn):
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [_walk(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: _walk(v, fn) for k, v in obj.items()}
    return obj


def numbers(text):
    return {n.replace(",", "") for n in re.findall(r"\d+(?:[.,]\d+)*", text)}


def checks(m, sources):
    letter, cv = m["coverLetter"], m["cv"]
    everything = letter + "\n" + plain_cv(m)
    words = len(letter.split())
    ungrounded = sorted(numbers(everything) - numbers(sources), key=len)
    sentences = re.split(r"(?<=[.!?])\s+|\n", everything)
    opportunity_misuse = [s for s in sentences if OPPORTUNITY.search(s) and DELIVERY_VERBS.search(s)]
    misattributed = [s.strip() for i, s in enumerate(sentences) for fig, owner in FIGURE_OWNERS.items()
                     if re.search(fig, s, re.I) and not re.search(owner, " ".join(sentences[max(0, i - 1):i + 1]), re.I)]
    rows = [
        ("Cover letter is 250 to 330 words", 250 <= words <= 330, f"{words} words"),
        ("No em or en dashes", not re.search(r"[—–]", everything), ""),
        ("No banned phrases", not any(b in everything.lower() for b in BANNED), ", ".join(b for b in BANNED if b in everything.lower())),
        ("Excluded project never mentioned", not EXCLUDED.search(everything), ""),
        ("No 'VP' for the wellbeing role", not VP_WELLBEING.search(everything), ""),
        ("$2.1B / $8B only with analysis verbs", not opportunity_misuse, " | ".join(opportunity_misuse)[:200]),
        ("Every number is in the sources", not ungrounded, ", ".join(ungrounded[:12])),
        ("Each locked figure sits with its own project", not misattributed, " | ".join(misattributed)[:240]),
        ("At most 4 roles, 5 bullets each", len(cv["experience"]) <= 4 and all(len(e["bullets"]) <= 5 for e in cv["experience"]),
         f"{len(cv['experience'])} roles"),
        ("Education populated", bool(cv["education"]), ""),
        ("Employer choice explained first in notes", bool(m["notes"]) and bool(re.search(r"employer|amazon|arcelik|arçelik", m["notes"][0], re.I)), ""),
    ]
    return [{"check": c, "pass": bool(ok), "detail": d} for c, ok, d in rows]


def plain_cv(m):
    cv, out = m["cv"], [m["cv"]["name"], m["cv"]["headline"], m["cv"]["contact"]]
    if cv["summary"]:
        out += ["", "PROFESSIONAL SUMMARY", cv["summary"]]
    for title, entries in (("PROFESSIONAL EXPERIENCE", cv["experience"]), ("EDUCATION", cv["education"])):
        if entries:
            out += ["", title]
            for e in entries:
                out.append(", ".join(x for x in (e["role"], e["org"]) if x) + (f"  ({e['dates']})" if e["dates"] else "")
                           + (f"  {e['location']}" if e["location"] else ""))
                out += [f"- {b}" for b in e["bullets"]]
    for title, items in (("SKILLS & COMPETENCIES", cv["skills"]), ("CERTIFICATIONS", cv["certifications"]), ("AWARDS", cv["awards"])):
        if items:
            out += ["", title] + [f"- {i}" for i in items]
    return "\n".join(x for x in out if x is not None)


def export(m, stem):
    import docx
    from docx.shared import Pt

    config.EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for kind, text in (("CV", plain_cv(m)), ("CoverLetter", m["coverLetter"])):
        d = docx.Document()
        d.styles["Normal"].font.name, d.styles["Normal"].font.size = "Arial", Pt(10.5)
        for line in (s.strip() for s in text.split("\n")):
            if not line:
                continue
            if re.fullmatch(r"[A-Z][A-Z &]+", line):
                d.add_paragraph().add_run(line).bold = True
            elif line.startswith("- "):
                d.add_paragraph(line[2:], style="List Bullet")
            else:
                d.add_paragraph(line)
        path = config.EXPORTS_DIR / f"Ayhan_Demir_{kind}_{stem}.docx"
        d.save(path)
        paths.append(str(path))
    md = config.EXPORTS_DIR / f"Ayhan_Demir_Materials_{stem}.md"
    md.write_text(f"# Cover letter\n\n{m['coverLetter']}\n\n# CV\n\n```\n{plain_cv(m)}\n```\n", encoding="utf-8")
    return paths + [str(md)]


def generate(job):
    """job: a board record with description (and ideally an ai.rag evidence pack). Returns materials + checks + files."""
    if not llm.available():
        raise RuntimeError("Add OPENAI_API_KEY to .env to draft materials.")
    pack = evidence_for(job)
    style_title, style_text = rag.get().best_document(f"{job['title']} {job['company']} cover letter", "cover_letter")
    system, user = build_messages(job, pack, style_title, style_text)
    draft = lambda prompt: _walk(llm.parse(config.LLM_MODEL, system, prompt, Materials, effort=config.REASONING_EFFORT).model_dump(), fix_dashes)
    sources = "\n".join([C.CANONICAL_FACTS, job.get("description") or "", style_text] + [e["text"] for e in pack])
    m = draft(user)
    report = first = checks(m, sources)
    failed = [c for c in report if not c["pass"]]
    if failed:  # one self-correction round: the model sees its draft and exactly which rules it broke
        feedback = "\n".join(f"- {c['check']}: {c['detail'] or 'failed'}" for c in failed)
        retry = draft(f"{user}\n\nYOUR PREVIOUS DRAFT:\n{json.dumps(m, ensure_ascii=False)}\n\n"
                      f"IT FAILED THESE CHECKS:\n{feedback}\nReturn the complete corrected draft, changing only what the checks require.")
        retry_report = checks(retry, sources)
        if sum(c["pass"] for c in retry_report) >= sum(c["pass"] for c in report):
            m, report = retry, retry_report
    stem = re.sub(r"[^A-Za-z0-9]+", "_", f"{job['company']}_{job['title']}")[:60].strip("_")
    return {"materials": m, "checks": report, "first_draft_checks": first, "repaired": bool(failed),
            "files": export(m, stem), "style_example": style_title, "evidence_used": len(pack),
            "prompt": {"system": system, "user": user}}
