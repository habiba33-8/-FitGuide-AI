"""A small BM25 ranker written from scratch (no heavy ML libraries).

Why BM25 and not embeddings? The knowledge base is small and domain specific, the app must run on a
serverless host with a tiny size limit, and BM25 is deterministic, fast and easy to evaluate. The Retriever
interface in retriever.py makes it possible to add an embedding retriever later (see docs/ARCHITECTURE.md)."""
from __future__ import annotations
import math, re
from collections import Counter

STOP = set("a an and are as at be but by for from has have how i if in is it its me my of on or so than that the their then there these they this to was we what when which who why will with you your can do does should would about into over per also not no need much many get use".split())
_word = re.compile(r"[a-z0-9]+|[\u0600-\u06FF]+")


def stem(w: str) -> str:
    for suf in ("ingly", "edly", "ing", "ies", "es", "ed", "ly", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokenize(text: str) -> list[str]:
    return [stem(w) for w in _word.findall(text.lower()) if w not in STOP and len(w) > 1]


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tokens = [tokenize(d) for d in docs]
        self.tf = [Counter(t) for t in self.tokens]
        self.len = [len(t) for t in self.tokens]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 0.0
        df: Counter = Counter()
        for t in self.tf:
            df.update(t.keys())
        n = len(docs)
        self.idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}

    def scores(self, query: str) -> list[float]:
        q = tokenize(query)
        out = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in q:
                f = tf.get(w, 0)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * self.len[i] / (self.avg or 1))
                s += self.idf.get(w, 0.0) * f * (self.k1 + 1) / denom
            out.append(s)
        return out
