"""SQLite job board: the same record shape as the artifact and the Lovable app."""
import json
import re
import sqlite3
import time

import candidate as C
import config

COLUMNS = ["id", "title", "company", "location", "status", "sub_status", "furthest", "applied_on", "last_activity",
           "added", "fit", "win", "source", "description", "ai"]
STAGE_INDEX = {k: i for i, (k, _) in enumerate(C.STAGES)}


def connect():
    config.DATA.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY, title TEXT, company TEXT, location TEXT,
            status TEXT DEFAULT 'new', sub_status TEXT, furthest INTEGER, applied_on TEXT, last_activity TEXT,
            added INTEGER, fit INTEGER, win INTEGER, source TEXT, description TEXT, ai TEXT)""")


GENERIC = {"gmbh", "se", "ag", "inc", "ltd", "llc", "the", "and", "group", "company", "m", "f", "d", "x", "w"}


def _words(s):
    return set(re.findall(r"\w+", (s or "").lower())) - GENERIC


def same_job(con, title, company):
    """Id of an existing row for the same role (same company, near-identical title), if any."""
    for r in con.execute("SELECT id, title, company FROM jobs"):
        a, b = _words(r["title"]), _words(title)
        if (_words(r["company"]) & _words(company)) and len(a & b) / max(1, len(a | b)) >= 0.8:
            return r["id"]
    return None


def upsert(job, fuzzy=True):
    """Insert a new job, or refresh the assessment of an existing one while keeping its pipeline status.
    Returns the id used, which may be an existing row's id for the same role."""
    row = {"status": "new", "sub_status": None, "furthest": None, "applied_on": None, "last_activity": None,
           "added": int(time.time() * 1000), **job}
    row["ai"] = json.dumps(row.get("ai") or {}, ensure_ascii=False)
    with connect() as con:
        if fuzzy and not con.execute("SELECT 1 FROM jobs WHERE id=?", (row["id"],)).fetchone():
            row["id"] = same_job(con, row["title"], row["company"]) or row["id"]
        con.execute(f"""INSERT INTO jobs ({','.join(COLUMNS)}) VALUES ({','.join('?' * len(COLUMNS))})
            ON CONFLICT(id) DO UPDATE SET title=excluded.title, company=excluded.company, location=excluded.location,
            fit=excluded.fit, win=excluded.win, source=excluded.source, ai=excluded.ai,
            description=COALESCE(NULLIF(excluded.description, ''), jobs.description)""",
                    [row.get(c) for c in COLUMNS])
    return row["id"]


def import_history(path=config.HISTORY_PATH):
    """Load the scored jobs exported from the Claude artifact (only ids not already on the board)."""
    if not path.exists():
        return 0
    with connect() as con:
        known = {r[0] for r in con.execute("SELECT id FROM jobs")}
    added = 0
    for j in json.loads(path.read_text()):
        if j["id"] in known:
            continue
        ai = j.get("ai") or {}
        upsert({"id": j["id"], "title": j["title"], "company": j["company"], "location": j.get("location", ""),
                "status": j.get("status", "new"), "sub_status": j.get("subStatus"), "furthest": j.get("furthest"),
                "applied_on": j.get("appliedOn"), "last_activity": j.get("lastActivity"), "added": j.get("added"),
                "fit": ai.get("score"), "win": ai.get("win"), "source": "artifact-history",
                "description": j.get("desc", ""), "ai": ai}, fuzzy=False)
        added += 1
    return added


def jobs():
    with connect() as con:
        rows = [dict(r) for r in con.execute("SELECT * FROM jobs ORDER BY added DESC")]
    for r in rows:
        r["ai"] = json.loads(r["ai"] or "{}")
    return rows


def get(job_id):
    return next((j for j in jobs() if j["id"] == job_id), None)


def set_status(job_id, status, sub_status=None):
    with connect() as con:
        cur = con.execute("SELECT furthest FROM jobs WHERE id=?", (job_id,)).fetchone()
        furthest = cur["furthest"] if cur else None
        if status == "saved" and sub_status in STAGE_INDEX:  # remember the furthest stage reached
            furthest = max(furthest or 0, STAGE_INDEX[sub_status])
        con.execute("UPDATE jobs SET status=?, sub_status=?, furthest=?, last_activity=? WHERE id=?",
                    (status, sub_status, furthest, time.strftime("%Y-%m-%d"), job_id))


def delete(job_id):
    with connect() as con:
        con.execute("DELETE FROM jobs WHERE id=?", (job_id,))


def funnel():
    """Applications by furthest stage reached. Rejections with no recorded stage count only as Applied."""
    saved = [j for j in jobs() if j["status"] == "saved" and j["sub_status"] != "notapplied"]
    rows = [("Applied", len(saved))]
    for key, label in C.STAGES[2:]:
        rows.append((label, sum((j["furthest"] or 0) >= STAGE_INDEX[key] for j in saved)))
    unknown = sum(j["furthest"] is None for j in saved)
    return rows, unknown
