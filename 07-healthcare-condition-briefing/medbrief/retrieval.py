"""Hybrid retrieval (vector + BM25, reciprocal rank fusion) over the `documents` Chroma collection.

Metadata filters (condition, classification, content_type) are applied BEFORE ranking, so documents a role
is not cleared for never reach the prompt.
"""

import math
import re
from collections import Counter
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma

from medbrief.config import get_settings
from medbrief.llm import get_embeddings

RRF_K = 60
COLLECTIONS = ("documents",)
_STOP = frozenset(["a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from", "how", "i", "if", "in", "is", "it", "of", "on", "or", "the", "to", "what", "when", "where", "which", "who", "why", "with", "my", "we", "our", "can"])


@lru_cache
def get_client() -> chromadb.ClientAPI:
    path = get_settings().chroma_dir
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(path), settings=ChromaSettings(anonymized_telemetry=False))


def get_store(name: str) -> Chroma:
    return Chroma(
        client=get_client(), collection_name=name, embedding_function=get_embeddings(),
        collection_metadata={"hnsw:space": "cosine", "index_fingerprint": get_settings().index_fingerprint},
    )


def _stem(t: str) -> str:
    for suf in ("ing", "ed", "es", "e", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]


class BM25:
    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [tokenize(d) for d in corpus]
        self.tfs = [Counter(d) for d in self.docs]
        self.avgdl = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df = Counter(t for d in self.docs for t in set(d))
        self.idf = {t: math.log(1 + (len(self.docs) - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for tf, doc in zip(self.tfs, self.docs):
            norm = self.k1 * (1 - self.b + self.b * len(doc) / self.avgdl)
            out.append(sum(self.idf.get(t, 0) * tf[t] * (self.k1 + 1) / (tf[t] + norm) for t in terms if t in tf))
        return out


class HybridRetriever:
    def __init__(self, collection: str):
        self.collection = collection
        self.store = get_store(collection)
        self._corpus: list[tuple[str, str, dict, list[float]]] | None = None

    def _load(self):
        if self._corpus is None:
            d = self.store.get(include=["documents", "metadatas", "embeddings"])
            self._corpus = list(zip(d["ids"], d["documents"], d["metadatas"], [list(e) for e in d["embeddings"]]))
        return self._corpus

    def search(self, query: str, k: int, where: dict | None = None) -> list[dict]:
        """`where` = metadata filter; a list value means "any of", e.g. {"zone": ["Z1-Inbound"], "robot_id": "R-1007"}."""
        def match(meta: dict) -> bool:
            return all(meta.get(f) in v if isinstance(v, (list, tuple)) else meta.get(f) == v for f, v in (where or {}).items())

        corpus = [c for c in self._load() if match(c[2])]
        if not corpus:
            return []
        qv = get_embeddings().embed_query(query)
        cosine = {cid: _cos(qv, emb) for cid, _, _, emb in corpus}
        lex = BM25([text for _, text, _, _ in corpus]).scores(query)
        by_vec = sorted(range(len(corpus)), key=lambda i: cosine[corpus[i][0]], reverse=True)[: k * 2]
        by_lex = [i for i in sorted(range(len(corpus)), key=lambda i: lex[i], reverse=True)[: k * 2] if lex[i] > 0]
        rrf: dict[int, float] = {}
        for ranking in (by_vec, by_lex):
            for rank, i in enumerate(ranking):
                rrf[i] = rrf.get(i, 0.0) + 1 / (RRF_K + rank + 1)
        top = sorted(rrf, key=rrf.get, reverse=True)[:k]
        return [
            {"id": corpus[i][0], "content": corpus[i][1], "metadata": corpus[i][2],
             "score": round(cosine[corpus[i][0]], 4), "rrf": round(rrf[i], 4)}
            for i in top
        ]


def _cos(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / ((math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))) or 1.0)


@lru_cache
def get_retrievers() -> dict[str, HybridRetriever]:
    return {name: HybridRetriever(name) for name in COLLECTIONS}
