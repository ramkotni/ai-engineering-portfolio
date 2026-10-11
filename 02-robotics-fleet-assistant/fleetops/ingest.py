"""Ingestion: robot incidents + maintenance logs (CSV rows) and the troubleshooting guide (Markdown with
tables) -> nomic-embed-text -> ChromaDB.   python -m fleetops.ingest
"""

import logging
import re

from langchain_core.documents import Document

from fleetops.chunking import chunk_markdown, contextual_header
from fleetops.config import get_settings
from fleetops.data import incident_text, maintenance_text, table
from fleetops.retrieval import COLLECTIONS, get_client, get_store

log = logging.getLogger(__name__)


def event_documents() -> list[Document]:
    docs = []
    for _, r in table("incidents").iterrows():
        meta = {k: str(r[k]) for k in ("event_id", "date", "robot_id", "zone", "model", "firmware", "event_type",
                                       "error_code", "severity")}
        docs.append(Document(page_content=incident_text(r), metadata={**meta, "doc_type": "incident",
                                                                       "downtime_min": int(r["downtime_min"])},
                             id=r["event_id"]))
    for _, r in table("maintenance_logs").iterrows():
        meta = {k: str(r[k]) for k in ("log_id", "date", "robot_id", "zone", "action")}
        docs.append(Document(page_content=maintenance_text(r), metadata={**meta, "doc_type": "maintenance"}, id=r["log_id"]))
    return docs


def knowledge_documents() -> list[Document]:
    s = get_settings()
    path = s.data_dir / "troubleshooting_guide.md"
    text = path.read_text(encoding="utf-8")
    doc_id = re.search(r"Document ID:\s*([\w-]+)", text).group(1)
    title = re.search(r"^#\s+(.+)$", text, re.MULTILINE).group(1).strip()
    body = re.sub(r"^Document ID:.*$", "", text, flags=re.MULTILINE)
    docs = []
    for i, c in enumerate(chunk_markdown(body, s.chunk_size, s.chunk_overlap, s.table_max_chars)):
        path_ = [p for p in c.section_path if p != title]
        docs.append(Document(
            page_content=f"{contextual_header(title, doc_id, c.section_path)}\n{c.text}",
            metadata={"doc_id": doc_id, "title": title, "section": path_[-1] if path_ else "Overview",
                      "content_type": c.content_type, "doc_type": "guide", "zone": "all"},
            id=f"{doc_id}::{i}"))
    return docs


def build_index() -> dict[str, int]:
    client = get_client()
    existing = {c.name for c in client.list_collections()}
    counts = {}
    for name, docs in (("events", event_documents()), ("knowledge", knowledge_documents())):
        if name in existing:
            client.delete_collection(name)
        get_store(name).add_documents(docs, ids=[d.id for d in docs])
        counts[name] = len(docs)
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
