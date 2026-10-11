"""Ingestion pipeline: extract -> normalise to Markdown -> structure-aware chunks -> embed ->
one Chroma collection per knowledge source.

Run:  python -m plant_assist.ingest
"""

import logging
from pathlib import Path

from langchain_core.documents import Document

from plant_assist.chunking import chunk_markdown, contextual_header
from plant_assist.config import get_settings
from plant_assist.loaders import SUPPORTED_SUFFIXES, load_document, parse_front_matter
from plant_assist.retrieval import get_chroma_client, get_vector_store
from plant_assist.sources import SOURCES, KnowledgeSource

__all__ = ["build_index", "ensure_index", "index_exists", "load_source_documents", "parse_front_matter"]

log = logging.getLogger(__name__)


def load_source_documents(source: KnowledgeSource) -> list[Document]:
    """Load every supported file of one source and return its chunks as LangChain Documents."""
    s = get_settings()
    files = sorted(p for p in Path(s.docs_dir, source.folder).iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES)
    out: list[Document] = []
    for path in files:
        doc = load_document(path)
        chunks = chunk_markdown(doc.markdown, s.chunk_size, s.chunk_overlap, s.table_max_chars)
        for i, chunk in enumerate(chunks):
            path_wo_title = [p for p in chunk.section_path if p != doc.title]
            out.append(
                Document(
                    page_content=f"{contextual_header(doc.title, doc.doc_id, chunk.section_path)}\n{chunk.text}",
                    metadata={
                        "source": source.name,
                        "doc_id": doc.doc_id,
                        "title": doc.title,
                        "section": path_wo_title[-1] if path_wo_title else "Overview",
                        "section_path": " > ".join(path_wo_title),
                        "content_type": chunk.content_type,
                        "chunk_index": i,
                        "revision": str(doc.meta.get("revision", "")),
                        "owner": str(doc.meta.get("owner", "")),
                        "file": path.name,
                    },
                )
            )
    return out


def build_index(reset: bool = True) -> dict[str, int]:
    """(Re)build every source collection. Returns chunk counts per source."""
    client = get_chroma_client()
    existing = {c.name for c in client.list_collections()}
    counts: dict[str, int] = {}
    for source in SOURCES.values():
        if reset and source.collection in existing:
            client.delete_collection(source.collection)
        docs = load_source_documents(source)
        if docs:
            ids = [f"{d.metadata['doc_id']}::{d.metadata['chunk_index']}" for d in docs]
            get_vector_store(source.name).add_documents(docs, ids=ids)
        counts[source.name] = len(docs)
        log.info("Indexed %d chunks into %s", len(docs), source.collection)
    return counts


def index_exists() -> bool:
    """True if every collection exists, is non-empty and matches the current embedding model + chunking."""
    client = get_chroma_client()
    names = {c.name for c in client.list_collections()}
    for src in SOURCES.values():
        if src.collection not in names:
            return False
        col = client.get_collection(src.collection)
        if col.count() == 0 or (col.metadata or {}).get("index_fingerprint") != get_settings().index_fingerprint:
            return False
    return True


def ensure_index() -> None:
    """Build the index on first start or when it is stale (used by the API / UI / container entrypoints)."""
    if not index_exists():
        build_index(reset=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    totals = build_index(reset=True)
    print(f"Indexed {sum(totals.values())} chunks: {totals}  ->  {get_settings().chroma_dir}")
