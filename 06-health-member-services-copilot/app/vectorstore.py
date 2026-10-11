"""Knowledge-base abstraction.

The graph only depends on the `KnowledgeBase` protocol, so the backing store can
be swapped (Chroma locally / in-container, Amazon Bedrock Knowledge Bases in a
managed deployment) without touching agent logic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    source: str
    section: str = ""
    score: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"content": self.content, "source": self.source, "section": self.section, "score": round(self.score, 4)}


class KnowledgeBase(Protocol):
    def search(self, query: str, k: int) -> list[RetrievedChunk]: ...

    def count(self) -> int: ...


class ChromaKnowledgeBase:
    def __init__(self, settings: Settings | None = None, embeddings=None):
        from langchain_chroma import Chroma

        from app.providers import get_embeddings

        self.settings = settings or get_settings()
        self.store = Chroma(
            collection_name=self.settings.collection_name,
            embedding_function=embeddings or get_embeddings(self.settings),
            persist_directory=str(self.settings.chroma_persist_dir),
            collection_metadata={"hnsw:space": "cosine"},
        )

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        results = self.store.similarity_search_with_relevance_scores(query, k=k)
        chunks = [
            RetrievedChunk(
                content=doc.page_content,
                source=doc.metadata.get("source", "unknown"),
                section=doc.metadata.get("section", ""),
                score=float(score),
                metadata=doc.metadata,
            )
            for doc, score in results
        ]
        threshold = self.settings.relevance_threshold
        kept = [c for c in chunks if c.score >= threshold]
        logger.debug("chroma search k=%s kept=%s/%s", k, len(kept), len(chunks))
        return kept

    def count(self) -> int:
        return self.store._collection.count()


class BedrockKnowledgeBase:
    """Managed alternative: Amazon Bedrock Knowledge Bases (S3 -> OpenSearch Serverless)."""

    def __init__(self, settings: Settings | None = None):
        from langchain_aws import AmazonKnowledgeBasesRetriever

        self.settings = settings or get_settings()
        if not self.settings.bedrock_kb_id:
            raise ValueError("BEDROCK_KB_ID must be set when VECTOR_BACKEND=bedrock_kb")
        self.retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=self.settings.bedrock_kb_id,
            region_name=self.settings.aws_region,
            retrieval_config={"vectorSearchConfiguration": {"numberOfResults": self.settings.retrieval_k}},
        )

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        docs = self.retriever.invoke(query)[:k]
        out = []
        for d in docs:
            loc = d.metadata.get("location", {}) or {}
            uri = (loc.get("s3Location") or {}).get("uri", "bedrock-kb")
            out.append(
                RetrievedChunk(
                    content=d.page_content,
                    source=uri.rsplit("/", 1)[-1],
                    score=float(d.metadata.get("score", 0.0)),
                    metadata=d.metadata,
                )
            )
        return [c for c in out if c.score >= self.settings.relevance_threshold]

    def count(self) -> int:
        return -1  # not cheaply available for managed KBs


def get_knowledge_base(settings: Settings | None = None) -> KnowledgeBase:
    s = settings or get_settings()
    if s.vector_backend == "bedrock_kb":
        return BedrockKnowledgeBase(s)
    return ChromaKnowledgeBase(s)
