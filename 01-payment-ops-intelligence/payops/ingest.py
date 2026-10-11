"""Ingestion: CSV incidents + HTML reports + Markdown rules -> embeddings (nomic-embed-text) -> ChromaDB.

    python -m payops.ingest
"""

import logging

from langchain_core.documents import Document

from payops.chunking import chunk_markdown, contextual_header
from payops.config import get_settings
from payops.loaders import LoadedDocument, incident_text, load_html, load_incidents, load_markdown
from payops.retrieval import COLLECTIONS, get_client, get_store

log = logging.getLogger(__name__)


def incident_documents() -> list[Document]:
    docs = []
    for r in load_incidents(get_settings().data_dir / "incidents.csv"):
        meta = {k: r[k] for k in ("incident_id", "date", "month", "system", "payment_type", "failure_category",
                                  "severity", "status", "detected_by")}
        meta |= {"amount_usd": r["amount_usd"], "resolution_time_hours": r["resolution_time_hours"],
                 "doc_type": "incident", "source_file": "incidents.csv"}
        docs.append(Document(page_content=incident_text(r), metadata=meta, id=r["incident_id"]))
    return docs


def _chunks(doc: LoadedDocument, doc_type: str) -> list[Document]:
    s = get_settings()
    out = []
    for i, c in enumerate(chunk_markdown(doc.markdown, s.chunk_size, s.chunk_overlap, s.table_max_chars)):
        path = [p for p in c.section_path if p != doc.title]
        out.append(Document(
            page_content=f"{contextual_header(doc.title, doc.doc_id, c.section_path)}\n{c.text}",
            metadata={"doc_id": doc.doc_id, "title": doc.title, "section": path[-1] if path else "Overview",
                      "section_path": " > ".join(path), "content_type": c.content_type, "doc_type": doc_type,
                      "source_file": doc.path.name, "chunk_index": i},
            id=f"{doc.doc_id}::{i}",
        ))
    return out


def knowledge_documents() -> list[Document]:
    data = get_settings().data_dir
    docs = []
    for html in sorted((data / "reports").glob("*.html")):
        docs += _chunks(load_html(html), "monitoring_report")
    for md in sorted(data.glob("*.md")):
        docs += _chunks(load_markdown(md), "business_rules")
    return docs


def build_index() -> dict[str, int]:
    client = get_client()
    existing = {c.name for c in client.list_collections()}
    counts = {}
    for name, docs in (("incidents", incident_documents()), ("knowledge", knowledge_documents())):
        if name in existing:
            client.delete_collection(name)
        get_store(name).add_documents(docs, ids=[d.id for d in docs])
        counts[name] = len(docs)
        log.info("Indexed %d documents into %s", len(docs), name)
    return counts


def index_exists() -> bool:
    client = get_client()
    names = {c.name for c in client.list_collections()}
    for name in COLLECTIONS:
        if name not in names:
            return False
        col = client.get_collection(name)
        if col.count() == 0 or (col.metadata or {}).get("index_fingerprint") != get_settings().index_fingerprint:
            return False
    return True


def ensure_index() -> None:
    if not index_exists():
        build_index()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print(f"Indexed: {build_index()} -> {get_settings().chroma_dir}")
