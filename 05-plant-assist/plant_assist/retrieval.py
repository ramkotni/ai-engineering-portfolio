"""Per-source hybrid retrievers (vector + BM25) backed by Chroma.

Each knowledge source lives in its own collection, so routing decides *where* to search
and hybrid search decides *what* to return. BM25 catches exact plant vocabulary (part
numbers, "gland retainer", alarm codes) that small embedding models blur together.
"""

import math
import re
from collections import Counter
from functools import lru_cache
from typing import Protocol

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma

from plant_assist.config import get_settings
from plant_assist.llm import get_embeddings
from plant_assist.sources import SOURCES

RRF_K = 60
_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from", "how", "i", "if",
    "in", "is", "it", "of", "on", "or", "the", "to", "what", "when", "where", "which", "who", "why",
    "with", "my", "we", "our", "should", "can",
})


class SourceRetriever(Protocol):
    def search(self, query: str, k: int) -> list[dict]: ...


@lru_cache
def get_chroma_client() -> chromadb.ClientAPI:
    path = get_settings().chroma_dir
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(path), settings=ChromaSettings(anonymized_telemetry=False)
    )


def get_vector_store(source_name: str) -> Chroma:
    return Chroma(
        client=get_chroma_client(),
        collection_name=SOURCES[source_name].collection,
        embedding_function=get_embeddings(),
        collection_metadata={
            "hnsw:space": "cosine",  # relevance score = cosine similarity
            "index_fingerprint": get_settings().index_fingerprint,  # detects model / chunking changes
        },
    )


def _stem(token: str) -> str:
    """Crude suffix stripping so 'spilled'/'spill' and 'replacing'/'replace' match."""
    for suffix in ("ing", "ed", "es", "e", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    return token


def tokenize(text: str) -> list[str]:
    return [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS]


class BM25:
    """Minimal Okapi BM25 - the corpus per source is small enough to keep in memory."""

    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = [tokenize(d) for d in corpus]
        self.tfs = [Counter(d) for d in self.docs]
        self.avgdl = sum(map(len, self.docs)) / max(len(self.docs), 1)
        df = Counter(term for d in self.docs for term in set(d))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}
        self.k1, self.b = k1, b

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for tf, doc in zip(self.tfs, self.docs):
            norm = self.k1 * (1 - self.b + self.b * len(doc) / self.avgdl)
            out.append(
                sum(self.idf.get(t, 0) * tf[t] * (self.k1 + 1) / (tf[t] + norm) for t in terms if t in tf)
            )
        return out


class HybridSourceRetriever:
    def __init__(self, source_name: str):
        self.source_name = source_name
        self.store = get_vector_store(source_name)
        self._bm25: BM25 | None = None
        self._corpus: list[tuple[str, str, dict]] = []  # (id, text, metadata)
        self._vectors: dict[str, list[float]] = {}       # stored chunk embeddings by id

    def _lexical_index(self) -> BM25:
        if self._bm25 is None:
            data = self.store.get(include=["documents", "metadatas", "embeddings"])
            self._corpus = list(zip(data["ids"], data["documents"], data["metadatas"]))
            self._vectors = {i: list(v) for i, v in zip(data["ids"], data["embeddings"])}
            self._bm25 = BM25([text for _, text, _ in self._corpus])
        return self._bm25

    def search(self, query: str, k: int) -> list[dict]:
        bm25 = self._lexical_index()
        candidates: dict[str, dict] = {}

        # Vector leg: cosine similarity is kept as the absolute relevance signal.
        vector_hits = self.store.similarity_search_with_relevance_scores(query, k=k * 2)
        for rank, (doc, score) in enumerate(vector_hits):
            key = doc.id or doc.page_content
            c = candidates.setdefault(key, self._chunk(doc.page_content, doc.metadata, key))
            c["score"] = round(float(score), 4)
            c["rrf"] += 1 / (RRF_K + rank + 1)

        # Lexical leg.
        lex = bm25.scores(query)
        lex_ranked = sorted(range(len(lex)), key=lambda i: lex[i], reverse=True)[: k * 2]
        for rank, i in enumerate(lex_ranked):
            if lex[i] <= 0:
                break
            doc_id, text, meta = self._corpus[i]
            c = candidates.setdefault(doc_id, self._chunk(text, meta, doc_id))
            c["bm25"] = round(lex[i], 3)
            c["rrf"] += 1 / (RRF_K + rank + 1)

        # Chunks found only lexically get a cosine score from their stored embedding,
        # so the grader can judge every candidate on the same scale.
        missing = [c for c in candidates.values() if c["score"] is None]
        if missing:
            q = get_embeddings().embed_query(query)
            for c in missing:
                c["score"] = round(_cosine(q, self._vectors[c.pop("_id")]), 4)
        for c in candidates.values():
            c.pop("_id", None)

        fused = sorted(candidates.values(), key=lambda c: c["rrf"], reverse=True)[:k]
        for c in fused:
            c["rrf"] = round(c["rrf"], 4)
        return fused

    def _chunk(self, content: str, meta: dict, chunk_id: str) -> dict:
        return {
            "_id": chunk_id,
            "source": self.source_name,
            "doc_id": meta.get("doc_id", ""),
            "title": meta.get("title", ""),
            "section": meta.get("section", ""),
            "section_path": meta.get("section_path", ""),
            "content_type": meta.get("content_type", "text"),
            "revision": meta.get("revision", ""),
            "content": content,
            "score": None,
            "bm25": 0.0,
            "rrf": 0.0,
        }


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)) or 1.0)


def get_retrievers() -> dict[str, SourceRetriever]:
    return {name: HybridSourceRetriever(name) for name in SOURCES}
