"""Retrieval over the candidate's own documents.

Per query:   dense (local bge embeddings in Chroma) + BM25 keywords
             -> Reciprocal Rank Fusion -> cross-encoder rerank (Cohere or local).
Per posting: every requirement is searched twice (its wording and a HyDE-style
             "what proof would look like" sentence), fused, reranked against the
             requirement, de-duplicated and packed into a token budget as [E#] evidence.
"""
import json
import re
from functools import lru_cache

import numpy as np

import config

STOP = set("a an the and or of to in for on with by at from as is are was were be been this that these those it its "
           "his he him their our your we you i my me not no but into over per via will can who what how".split())


def tokens(text):
    return [w for w in re.findall(r"[a-z0-9$%]+(?:[.,][0-9]+)*", text.lower()) if w not in STOP]


@lru_cache(None)
def embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(config.EMBED_MODEL)


def embed(texts, query=False):
    prompt = config.EMBED_QUERY_PROMPT if query else None
    return embedder().encode(list(texts), normalize_embeddings=True, prompt=prompt, show_progress_bar=False)


@lru_cache(None)
def local_reranker():
    from sentence_transformers import CrossEncoder
    return CrossEncoder(config.LOCAL_RERANK_MODEL)


@lru_cache(None)
def cohere_client():
    import cohere
    return cohere.ClientV2(api_key=config.COHERE_API_KEY)


def reranker_name():
    if config.RERANKER != "auto":
        return config.RERANKER
    return "cohere" if config.COHERE_API_KEY else "local"


def rrf(*rankings, k=60):
    """Reciprocal Rank Fusion: rank-based, so dense and BM25 scores never need calibrating."""
    scores = {}
    for ranking in rankings:
        for rank, (cid, _) in enumerate(ranking):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: -x[1])


class Retriever:
    def __init__(self):
        import chromadb
        from rank_bm25 import BM25Okapi

        self.col = chromadb.PersistentClient(path=str(config.CHROMA_DIR)).get_collection(config.COLLECTION)
        self.chunks = [json.loads(line) for line in config.CHUNKS_PATH.open(encoding="utf-8")]
        self.by_id = {c["id"]: c for c in self.chunks}
        self.bm25 = BM25Okapi([tokens(c["context"] + " " + c["text"]) for c in self.chunks])
        got = self.col.get(include=["embeddings"])
        self.vec = dict(zip(got["ids"], np.asarray(got["embeddings"])))
        self.reranker = reranker_name()
        self.rerank_errors = []

    # ---- single-query stages ----
    def dense(self, query, k=20, where=None):
        res = self.col.query(query_embeddings=embed([query], query=True).tolist(), n_results=k, where=where)
        return [(cid, 1.0 - d) for cid, d in zip(res["ids"][0], res["distances"][0])]

    def sparse(self, query, k=20):
        scores = self.bm25.get_scores(tokens(query))
        return [(self.chunks[i]["id"], float(scores[i])) for i in np.argsort(-scores)[:k] if scores[i] > 0]

    def rerank(self, query, ids, top_n=5):
        ids = list(dict.fromkeys(ids))
        if not ids or self.reranker == "none":
            return [(cid, 0.0) for cid in ids[:top_n]]
        docs = [self.by_id[cid]["context"] + "\n" + self.by_id[cid]["text"] for cid in ids]
        if self.reranker == "cohere":
            try:
                res = cohere_client().rerank(model=config.COHERE_RERANK_MODEL, query=query, documents=docs, top_n=top_n)
                return [(ids[r.index], float(r.relevance_score)) for r in res.results]
            except Exception as e:  # bad key, quota, network: fall back to the local model
                self.rerank_errors.append(str(e)[:200])
                self.reranker = "local"
        scores = local_reranker().predict([(query, d) for d in docs], show_progress_bar=False)
        return [(ids[i], float(scores[i])) for i in np.argsort(-scores)[:top_n]]

    def search(self, query, k=5, pool=20, mode="hybrid+rerank", trace=None):
        """mode: dense | bm25 | hybrid | hybrid+rerank. Fills `trace` with every stage when given a dict."""
        dense, bm25 = self.dense(query, pool), self.sparse(query, pool)
        fused = rrf(dense, bm25)[:pool]
        if trace is not None:
            trace.update(dense=dense, bm25=bm25, fused=fused)
        if mode == "dense":
            ranked = dense
        elif mode == "bm25":
            ranked = bm25
        elif mode == "hybrid":
            ranked = fused
        else:
            ranked = self.rerank(query, [cid for cid, _ in fused], top_n=k)
            if trace is not None:
                trace["reranked"] = ranked
        return [{**self.by_id[cid], "score": round(score, 4)} for cid, score in ranked[:k]]

    # ---- per-posting evidence pack ----
    def evidence_pack(self, requirements, per_req=2, per_doc=4, budget=config.EVIDENCE_BUDGET, max_sim=0.93):
        """requirements: dicts with id, ask, evidence_query, in priority order.
        per_doc keeps sources varied, max_sim drops the same story told in two documents."""
        pack, used = [], 0
        for req in requirements:
            rankings = [self.dense(req["ask"]), self.dense(req["evidence_query"]),
                        self.sparse(req["ask"]), self.sparse(req["evidence_query"])]
            candidates = [cid for cid, _ in rrf(*rankings)
                          if self.by_id[cid]["doc_type"] not in config.EVIDENCE_EXCLUDE_TYPES][:20]
            taken = 0
            ranked = self.rerank(req["ask"], candidates, top_n=8)
            bonus = 0.1 if self.reranker == "cohere" else 1.0  # small source-authority prior, in the reranker's scale
            ranked.sort(key=lambda x: -(x[1] + bonus * (self.by_id[x[0]]["doc_type"] in config.PRIMARY_TYPES)))
            for cid, score in ranked:
                if taken == per_req:
                    break
                same = next((e for e in pack if e["id"] == cid), None)
                if same:  # already in the pack: it now supports this requirement too
                    same["supports"].append(req["id"])
                    taken += 1
                    continue
                chunk = self.by_id[cid]
                if any(float(self.vec[cid] @ self.vec[e["id"]]) > max_sim for e in pack):
                    continue  # near-duplicate of evidence already packed
                if sum(e["doc_title"] == chunk["doc_title"] for e in pack) >= per_doc:
                    continue
                if used + chunk["tokens"] > budget:
                    break
                pack.append({"eid": f"E{len(pack) + 1}", "id": cid, "supports": [req["id"]], "score": round(score, 3),
                             "doc_title": chunk["doc_title"], "doc_type": chunk["doc_type"],
                             "section": chunk["section"], "text": chunk["text"], "tokens": chunk["tokens"]})
                used += chunk["tokens"]
                taken += 1
        return pack

    def best_document(self, query, doc_type):
        """Full text of the most relevant document of one type (metadata-filtered dense search)."""
        hits = self.dense(query, k=1, where={"doc_type": doc_type})
        if not hits:
            return None, ""
        title = self.by_id[hits[0][0]]["doc_title"]
        return title, "\n\n".join(c["text"] for c in self.chunks if c["doc_title"] == title)


@lru_cache(None)
def get():
    return Retriever()


def reset():
    get.cache_clear()
