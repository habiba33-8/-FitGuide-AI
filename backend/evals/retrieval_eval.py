"""Retrieval evaluation: for each labelled question, is a correct knowledge-base document in the top results?
Metrics: hit@1, hit@3 (is the right document in the top 1/3 chunks) and MRR (mean reciprocal rank).
Baseline: plain word overlap, to show BM25 actually adds value. Run:  python -m evals.retrieval_eval"""
from __future__ import annotations
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from fitguide.rag.retriever import kb_chunks, retrieve
from fitguide.rag.bm25 import tokenize

DATA = pathlib.Path(__file__).parent / "data" / "retrieval_queries.json"


def doc_of(chunk_id: str) -> str:
    return chunk_id.split("#")[0]


def baseline(q: str, k: int = 3) -> list[str]:
    qt = set(tokenize(q))
    scored = sorted(((len(qt & set(tokenize(c.title + " " + c.text))), c.id) for c in kb_chunks()), reverse=True)
    return [i for s, i in scored[:k] if s > 0]


def evaluate(fn) -> dict:
    qs = json.loads(DATA.read_text(encoding="utf-8"))
    h1 = h3 = 0
    rr = 0.0
    misses = []
    for item in qs:
        ranked = [doc_of(i) for i in fn(item["q"])]
        exp = set(item["expect"])
        rank = next((n for n, d in enumerate(ranked, 1) if d in exp), None)
        h1 += rank == 1
        h3 += rank is not None and rank <= 3
        rr += 1 / rank if rank else 0
        if rank is None or rank > 3:
            misses.append(item["q"])
    n = len(qs)
    return {"n": n, "hit@1": round(h1 / n, 3), "hit@3": round(h3 / n, 3), "mrr": round(rr / n, 3), "misses": misses}


def run() -> dict:
    bm = evaluate(lambda q: [r.id for r in retrieve(q, None, k=3, min_score=0.0)])
    base = evaluate(lambda q: baseline(q))
    return {"bm25": bm, "word_overlap_baseline": base}


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, ensure_ascii=False))
