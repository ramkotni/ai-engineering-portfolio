"""Fixtures: fake chat model + keyword retrievers over the real sample data (no Ollama / Chroma needed)."""

import pytest
from langchain_core.documents import Document
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from fleetops.config import Settings
from fleetops.ingest import event_documents, knowledge_documents
from fleetops.retrieval import BM25


class KeywordRetriever:
    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.calls: list[tuple] = []

    def search(self, query: str, k: int, where: dict | None = None) -> list[dict]:
        self.calls.append((query, where))

        def match(m):
            return all(m.get(f) in v if isinstance(v, (list, tuple)) else m.get(f) == v for f, v in (where or {}).items())

        docs = [d for d in self.docs if match(d.metadata)]
        scores = BM25([d.page_content for d in docs]).scores(query) if docs else []
        ranked = sorted(zip(docs, scores), key=lambda t: t[1], reverse=True)[:k]
        return [{"id": d.id, "content": d.page_content, "metadata": d.metadata, "score": 0.8, "rrf": s} for d, s in ranked]


@pytest.fixture(scope="session")
def retrievers():
    return {"events": KeywordRetriever(event_documents()), "knowledge": KeywordRetriever(knowledge_documents())}


@pytest.fixture
def settings(tmp_path):
    return Settings(_env_file=None, audit_log_path=tmp_path / "audit.jsonl")


def fake_llm(*answers: str) -> GenericFakeChatModel:
    return GenericFakeChatModel(messages=iter([AIMessage(content=a) for a in answers]))
