"""Drive mirror -> text -> canonicalised -> section-aware chunks -> local embeddings -> Chroma.

Tailoring for a career portfolio:
  * canonicalisation: paragraphs about the excluded project are dropped and
    titles the canonical record forbids are rewritten, so retrieval can never
    surface a claim the candidate has ruled out;
  * section-aware chunking that keeps case-study sections, interview questions
    and table rows together, repeating a table's header row in each piece;
  * a contextual header ("doc > section > subsection") embedded with every chunk;
  * tags for signature projects and pillars on every chunk.
"""
import json
import re
from pathlib import Path

import tiktoken

import candidate as C
import config

ENC = tiktoken.get_encoding("cl100k_base")
LOADABLE = {".md", ".txt", ".docx", ".pdf", ".pptx", ".json"}
DOC_TYPES = [("cover_letter", r"cover ?letter"), ("cv", r"\bcv\b|resume|lebenslauf"), ("case_study", r"case stud"),
             ("strategy_map", r"strategic map"), ("career_narrative", r"narrative"),
             ("interview_prep", r"interview|hm questions|core ?projects"), ("one_pager", r"one ?pagers?"),
             ("portfolio_data", r"portfolio data"), ("linkedin", r"linkedin")]
MAJOR = re.compile(r"^(?:#{1,3} .+|Case Study \d+.*|Question \d+:.*|SERVICE \d+ OF \d+|STEP \d+.*|"
                   r"Foundation Chapter.*|Phase \d+[AB]? [—-].*|\d{1,2}\.\s{1,3}\S.{3,140}|Slide \d+.*)$")
MINOR = re.compile(r"^(?:[A-ZÇĞİÖŞÜ][A-ZÇĞİÖŞÜ0-9 &·,/()'’:.\-–—]{2,70}|(?:Primary|Backup|Supporting evidence): .{5,160})$")
PRIORITY_TAG = re.compile(r"^(HIGH|MEDIUM|LOW)$")
EXCLUDED = re.compile("|".join(C.EXCLUDED_CLAIMS), re.I)
EXCLUDED_SENTENCE = re.compile(r"[^.!?\n]*(?:" + "|".join(C.EXCLUDED_CLAIMS) + r")[^.!?\n]*[.!?]?\s*", re.I)


def ntok(text):
    return len(ENC.encode(text))


def doc_type(title):
    t = re.sub(r"[_\-]+", " ", title.lower())
    return next((name for name, pat in DOC_TYPES if re.search(pat, t)), "other")


# ---------- loading ----------
def load_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".docx":
        import docx
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        d, out = docx.Document(str(path)), []
        for el in d.element.body.iterchildren():  # body order, so tables stay where they were
            if el.tag.endswith("}p"):
                p = Paragraph(el, d)
                if p.text.strip():
                    heading = (p.style.name or "").lower().startswith(("heading", "title"))
                    out.append(("## " if heading else "") + p.text.strip())
            elif el.tag.endswith("}tbl"):
                rows = ["| " + " | ".join(c.text.strip() for c in r.cells) + " |" for r in Table(el, d).rows]
                out.append("\n".join(rows))
        return "\n\n".join(out)
    if ext == ".pdf":
        from pypdf import PdfReader
        return "\n\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if ext == ".pptx":
        from pptx import Presentation
        slides = []
        for i, s in enumerate(Presentation(str(path)).slides, 1):
            texts = [sh.text_frame.text.strip() for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()]
            slides.append(f"Slide {i}\n\n" + "\n\n".join(texts))
        return "\n\n".join(slides)
    if ext == ".json":
        return json_to_text(json.loads(path.read_text(encoding="utf-8")))
    raise ValueError(f"unsupported file type: {path.name}")


def json_to_text(obj):
    """Portfolio JSON -> one '## section' per top-level key or list item, with 'key: value' lines."""
    def lines(o, prefix=""):
        if isinstance(o, dict):
            return [x for k, v in o.items() for x in lines(v, f"{prefix}{k} ")]
        if isinstance(o, list) and all(not isinstance(v, (dict, list)) for v in o):
            return [f"{prefix.strip()}: {', '.join(map(str, o))}"] if o else []
        if isinstance(o, list):
            return [x for v in o for x in lines(v, prefix)]
        return [f"{prefix.strip()}: {o}"] if str(o).strip() else []
    items = obj.items() if isinstance(obj, dict) else enumerate(obj)
    out = []
    for key, val in items:
        for i, item in enumerate(val if isinstance(val, list) else [val]):
            name = item.get("name") or item.get("title") or f"{key} {i + 1}" if isinstance(item, dict) else f"{key}"
            out.append(f"## {name}\n\n" + "\n".join(lines(item)))
    return "\n\n".join(out)


# ---------- cleaning and canonicalisation ----------
def clean(text):
    text = text.replace("\r", "").replace("**", "")
    text = re.sub(r"\\([#$.\[\]&~*_+\-!()|])", r"\1", text)  # markdown escapes from Drive exports
    text = re.sub(r"[ \t]+\n", "\n", text)
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if not PRIORITY_TAG.match(ln) and not re.fullmatch(r"\|(?:\s*:?-+:?\s*\|)+", ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def canonicalize(text):
    """Rewrite what the canonical record overrides; remove the excluded project at the smallest unit:
    a sentence in prose, a row in a table, the whole table when its title row is about it."""
    replaced = removed = 0
    for pattern, replacement in C.CANONICAL_REPLACEMENTS:
        text, n = re.subn(pattern, replacement, text)
        replaced += n
    kept = []
    for block in re.split(r"\n\s*\n", text):
        if not EXCLUDED.search(block):
            kept.append(block)
            continue
        if block.lstrip().startswith("|"):
            rows = block.split("\n")
            title_row = next((r for r in rows if re.search(r"\w", r)), "")
            rows = [] if EXCLUDED.search(title_row) else [r for r in rows if not EXCLUDED.search(r)]
            block = "\n".join(rows)
        else:
            block = EXCLUDED_SENTENCE.sub("", block).strip()
        removed += 1
        if len(re.findall(r"\w+", block)) >= 4:
            kept.append(block)
    return "\n\n".join(kept), {"replaced": replaced, "redacted_blocks": removed}


# ---------- section-aware chunking ----------
def split_sections(text):
    """[(major, minor, block)] where major/minor are the nearest headings above the block."""
    major, minor, out = "", "", []
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    i = 0
    while i < len(blocks):
        b = blocks[i]
        first = b.split("\n")[0]
        if "\n" not in b and MAJOR.match(b):
            major, minor = b.lstrip("# ").strip(), ""
            if len(major) < 25 and i + 1 < len(blocks) and "\n" not in blocks[i + 1] and len(blocks[i + 1]) < 90:
                major += " · " + blocks[i + 1]  # "SERVICE 1 OF 4" + its title line
                i += 1
        elif "\n" not in b and MINOR.match(b) and not first.startswith("|"):
            minor = b.title() if b.isupper() and b.isascii() else b
        else:
            out.append((major, minor, b))
        i += 1
    return out


def units(block):
    """Split an oversized block into packable units: table rows (header repeated) or sentences."""
    if ntok(block) <= config.CHUNK_TOKENS:
        return [block]
    lines = block.split("\n")
    if lines[0].startswith("|"):
        header, rows = (lines[0], lines[1:]) if re.search(r"\w", lines[0]) else ("", lines[1:])
        return [(header + "\n" + r).strip() for r in rows]
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9$])", block) if s.strip()]


def tag(text):
    t = text.lower()
    projects = [name for name, aliases in C.SIGNATURE_PROJECTS.items()
                if any(re.search(rf"(?<![a-z]){re.escape(a)}(?![a-z])", t) for a in aliases)]
    hits = {key: sum(bool(re.search(rf"(?<![a-z]){re.escape(k)}", t)) for k in kws) for key, _, _, kws in C.BUCKETS}
    pillars = [k for k, n in sorted(hits.items(), key=lambda x: -x[1]) if n][:3]
    return projects, pillars


def chunk_document(text, meta):
    title = re.sub(r"\.(docx|pdf|pptx|md|json|txt)$", "", meta["title"], flags=re.I).replace("_", " ")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    chunks, groups = [], {}
    for major, minor, block in split_sections(text):  # merge consecutive blocks of the same section
        groups.setdefault((major, minor), []).append(block)
    for (major, minor), blocks in groups.items():
        header = " › ".join(x for x in (title, major, minor) if x)
        buf, size, fresh = [], 0, 0  # fresh = units added since the last flush
        def flush():
            body = "\n\n".join(buf)
            projects, pillars = tag(header + " " + body)
            chunks.append({"id": f"{slug}-{len(chunks):03d}", "doc_id": meta.get("id", ""), "doc_title": title,
                           "doc_type": doc_type(meta["title"]), "folder": meta.get("folder", ""),
                           "modified": meta.get("modifiedTime", "")[:10], "url": meta.get("viewUrl", ""),
                           "section": major, "subsection": minor, "context": f"[{header}]",
                           "projects": "|".join(projects), "pillars": "|".join(pillars),
                           "tokens": ntok(body), "text": body})
        for unit in (u for b in blocks for u in units(b)):
            n = ntok(unit)
            if fresh and size + n > config.CHUNK_TOKENS:
                flush()
                tail = buf[-1] if ntok(buf[-1]) <= config.CHUNK_OVERLAP else ""  # overlap: carry a short last unit
                buf, size, fresh = ([tail], ntok(tail), 0) if tail else ([], 0, 0)
            buf.append(unit)
            size += n
            fresh += 1
        if fresh:
            flush()
    return chunks


# ---------- index ----------
def manifest():
    path = config.DRIVE_DIR / "manifest.json"
    entries = json.loads(path.read_text()) if path.exists() else []
    listed = {e["path"] for e in entries}
    for f in sorted(config.DRIVE_DIR.iterdir()):  # files dropped into the folder by hand are indexed too
        if f.suffix.lower() in LOADABLE and f.name != "manifest.json" and f.name not in listed:
            entries.append({"id": "", "title": f.name, "path": f.name, "folder": "(local)", "source": "local-file"})
    return entries


def run():
    from rag import embed, reset
    import chromadb

    docs, chunks = [], []
    for meta in manifest():
        text, stats = canonicalize(clean(load_text(config.DRIVE_DIR / meta["path"])))
        doc_chunks = chunk_document(text, meta)
        chunks += doc_chunks
        docs.append({"title": meta["title"], "type": doc_type(meta["title"]), "folder": meta.get("folder", ""),
                     "modified": meta.get("modifiedTime", "")[:10], "chunks": len(doc_chunks),
                     "tokens": sum(c["tokens"] for c in doc_chunks), **stats})
    config.CHUNKS_PATH.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in chunks), encoding="utf-8")

    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    if config.COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(config.COLLECTION)
    col = client.create_collection(config.COLLECTION, embedding_function=None, metadata={"hnsw:space": "cosine"})
    vectors = embed([c["context"] + "\n" + c["text"] for c in chunks])
    meta_keys = ("doc_id", "doc_title", "doc_type", "folder", "modified", "url", "section", "subsection",
                 "projects", "pillars", "tokens")
    col.add(ids=[c["id"] for c in chunks], embeddings=vectors.tolist(), documents=[c["text"] for c in chunks],
            metadatas=[{k: c[k] for k in meta_keys} for c in chunks])
    reset()
    return {"docs": docs, "chunks": len(chunks), "dim": int(vectors.shape[1]), "collection": col.count()}


if __name__ == "__main__":
    report = run()
    for d in report["docs"]:
        print(f"{d['chunks']:>3} chunks {d['tokens']:>6} tok  redacted={d['redacted_blocks']} replaced={d['replaced']}  {d['title']}")
    print(f"{report['chunks']} chunks, {report['dim']}-dim vectors, collection count {report['collection']}")
