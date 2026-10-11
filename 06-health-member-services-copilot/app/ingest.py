"""Document ingestion pipeline: load -> header-aware chunk -> embed -> Chroma.

Run:  python -m app.ingest --reset
"""
from __future__ import annotations

import argparse
import hashlib
import logging
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from app.config import Settings, get_settings
from app.logging_config import setup_logging

logger = logging.getLogger(__name__)


def load_markdown(docs_dir: Path) -> list[Document]:
    docs = []
    for path in sorted(docs_dir.glob("*.md")):
        docs.append(Document(page_content=path.read_text(encoding="utf-8"), metadata={"source": path.name}))
    return docs


def chunk_documents(docs: list[Document], settings: Settings) -> list[Document]:
    """Split on markdown headers first (keeps a section's facts together), then by size.

    Each chunk is prefixed with "<doc title> > <section>" ("contextual chunk
    headers") so the embedding knows *which plan/policy* a number belongs to -
    critical when Gold PPO and Silver HMO share near-identical wording.
    """
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "title"), ("##", "section")], strip_headers=True
    )
    size_splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
    )
    chunks: list[Document] = []
    for doc in docs:
        for section_doc in header_splitter.split_text(doc.page_content):
            title = section_doc.metadata.get("title", "")
            section = section_doc.metadata.get("section", "")
            for i, piece in enumerate(size_splitter.split_text(section_doc.page_content)):
                header = " > ".join(p for p in (title, section) if p)
                chunks.append(
                    Document(
                        page_content=f"{header}\n{piece}" if header else piece,
                        metadata={"source": doc.metadata["source"], "title": title, "section": section, "part": i},
                    )
                )
    return chunks


def chunk_id(doc: Document) -> str:
    key = f"{doc.metadata['source']}|{doc.metadata.get('section')}|{doc.metadata.get('part')}|{doc.page_content}"
    return hashlib.sha256(key.encode()).hexdigest()[:24]


def ingest(settings: Settings | None = None, reset: bool = False, embeddings=None) -> int:
    from app.vectorstore import ChromaKnowledgeBase

    s = settings or get_settings()
    kb = ChromaKnowledgeBase(s, embeddings=embeddings)
    if reset:
        kb.store.reset_collection()
    docs = load_markdown(s.docs_dir)
    chunks = chunk_documents(docs, s)
    ids = [chunk_id(c) for c in chunks]
    # Deterministic IDs make re-ingestion idempotent (upsert, no duplicates).
    kb.store.add_documents(chunks, ids=ids)
    logger.info(
        "ingested",
        extra={"extra_fields": {"files": len(docs), "chunks": len(chunks), "collection": s.collection_name}},
    )
    return len(chunks)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest policy documents into Chroma")
    parser.add_argument("--reset", action="store_true", help="drop and rebuild the collection")
    args = parser.parse_args()
    s = get_settings()
    setup_logging(s.log_level)
    n = ingest(s, reset=args.reset)
    print(f"Ingested {n} chunks into '{s.collection_name}' at {s.chroma_persist_dir}")


if __name__ == "__main__":
    main()
