"""Deterministic scoring: the artifact's offline keyword scorer, the rubric's
hard rules as guardrails on the LLM's numbers, and output sanitising."""
import re

import candidate as C

FRAC = [0, 0.5, 0.8, 1.0]  # share of a bucket's weight earned by 0, 1, 2, 3+ keyword hits
EXCLUDED = re.compile("|".join(C.EXCLUDED_CLAIMS), re.I)
LEVEL_CODE = re.compile(C.LEVEL_CODES)


def clamp(v):
    try:
        return max(0, min(100, round(float(v))))
    except (TypeError, ValueError):
        return None


def fit_tier(fit):
    return "strong" if fit >= 65 else "adjacent" if fit >= 35 else "mismatch"


def win_tier(win):
    if win is None:
        return ""
    return ("Candidate to beat" if win >= 78 else "In contention" if win >= 55 else
            "Likely out-competed" if win >= 35 else "Named screen" if win >= 15 else "Does not compete")


def company_tier(company):
    c = (company or "").lower().strip()
    for key, names in C.TIERS.items():
        if any(c == n.lower() or re.search(rf"(^|[^a-z0-9]){re.escape(n.lower())}([^a-z0-9]|$)", c) for n in names):
            return key
    return "other"


def offline_score(title, company, location, desc, exclude=C.EXCLUDE_TITLES):
    """Keyword fallback used when the LLM is unavailable. Same weights and gates as the artifact."""
    text = f"{title} {company} {location} {desc}".lower()
    contrib = {}
    for key, name, weight, kws in C.BUCKETS:
        matched = [k for k in kws if k in text]
        contrib[key] = (weight * FRAC[min(len(matched), 3)], matched)
    skills = round(min(100, sum(p for p, _ in contrib.values())))
    english = any(s in text for s in C.ENGLISH_WORKING)
    german_req = any(s in text for s in C.GERMAN_REQUIRED)
    junior = any(s in text for s in C.JUNIOR) and not any(s in text for s in C.SENIOR)
    loc_gate = not any(s in text for s in C.BERLIN_OK)
    excluded = any(t in (title or "").lower() for t in exclude)
    german_post = sum(w in f" {text} " for w in C.GERMAN_WORDS) >= 4
    fit = clamp(skills + 5 * english - 30 * junior - 25 * loc_gate - 70 * excluded - 10 * german_post)
    ranked = [k for k, _ in sorted(contrib.items(), key=lambda x: -x[1][0]) if contrib[k][0] > 0]
    gates = [g for g, on in [("Reads as junior or entry level", junior), ("Location may not fit Berlin or remote", loc_gate),
                             ("Excluded role type in title", excluded), ("German-language posting", german_post),
                             ("Fluent German required", german_req)] if on]
    summary = ("Strongest on " + " and ".join(C.PILLAR_SHORT[k] for k in ranked[:2]) + "." if ranked
               else "No portfolio keywords detected. Check the pasted text captured the requirements.")
    return {
        "title": title, "company": company, "location": location, "level": "", "levelBand": "unclear",
        "workingLanguage": "English" if english else "German" if german_post else "", "germanRequired": german_req,
        "germanLanguagePost": german_post, "roleType": "", "requirement_matches": [],
        "strong": [{"text": f"{C.PILLAR_SHORT[k]}: {', '.join(contrib[k][1][:5])}", "evidence_ids": []} for k in ranked[:3]],
        "reframeable": [], "gaps": gates, "blockers": [{"text": g, "kind": "screen"} for g in gates if "German" in g],
        "evidence": "argued", "disciplineFit": fit_tier(fit), "pillar": C.PILLAR_SHORT[ranked[0]] if ranked else "",
        "fitRole": "", "signatureProjects": [], "keySkills": [], "tools": [], "postedDate": "",
        "fit": fit, "win": None, "winWhy": "", "recommendation": summary + " Offline keyword score: rescore with the LLM for Win.",
    }


def guard(a, evidence_ids):
    """Enforce the rubric's hard rules on the LLM output. Returns (assessment, notes on what changed)."""
    notes = []
    a["fit"], a["win"] = clamp(a.get("fit")), clamp(a.get("win"))
    for key in ("strong", "reframeable"):
        for p in a.get(key, []):
            bad = [e for e in p["evidence_ids"] if e not in evidence_ids]
            if bad:
                p["evidence_ids"] = [e for e in p["evidence_ids"] if e in evidence_ids]
                notes.append(f"Removed citation(s) {', '.join(bad)} that are not in the evidence pack.")
    for m in a.get("requirement_matches", []):
        m["evidence_ids"] = [e for e in m["evidence_ids"] if e in evidence_ids]
    screens = [b for b in a["blockers"] if b["kind"] == "screen"]
    if a.get("germanRequired") and not any("german" in b["text"].lower() for b in screens):
        a["blockers"].append({"text": "Requires business-fluent German; he is B1+", "kind": "screen"})
        screens = [b for b in a["blockers"] if b["kind"] == "screen"]
        notes.append("Added a German-language screen because the posting requires fluent German.")
    if screens and a["win"] is not None and a["win"] > 25:
        notes.append(f"Win {a['win']} capped at 25: hard screen ({screens[0]['text']}).")
        a["win"] = 25
    if a["fit"] is not None and a["fit"] >= 85 and len(a["gaps"]) > 1:
        notes.append(f"Fit {a['fit']} capped at 84: 85+ allows at most one minor gap, found {len(a['gaps'])}.")
        a["fit"] = 84
    if a.get("evidence") != "direct" and a["win"] is not None and a["win"] > 70:
        notes.append(f"Win {a['win']} capped at 70: best evidence is {a.get('evidence')}, not direct.")
        a["win"] = 70
    return a, notes


def _clean_text(s):
    s = LEVEL_CODE.sub("Single-Threaded Leader scope", s)
    for pattern, replacement in C.CANONICAL_REPLACEMENTS:
        s = re.sub(pattern, replacement, s)
    return re.sub(r"[^.!?]*(?:" + "|".join(C.EXCLUDED_CLAIMS) + r")[^.!?]*[.!?]?\s*", "", s, flags=re.I).strip()


def sanitize(obj):
    """Recursively apply the profile's output rules: no level codes, canonical titles, no excluded project."""
    if isinstance(obj, str):
        return _clean_text(obj)
    if isinstance(obj, list):
        items = [sanitize(x) for x in obj]
        return [x for x in items if x not in ("", None) and not (isinstance(x, dict) and x.get("text") == "")]
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    return obj
