"""Ingestion pipeline: PDF / Word / HTML / Markdown / CSV + extracted images -> chunks -> nomic-embed-text -> ChromaDB.

    python -m supplykb.ingest            # uses cached image captions; captions new images if the vision model is available
    python -m supplykb.ingest --no-vision

Chunk types (metadata content_type): text | table | mixed | image (caption of an extracted figure) | record (CSV row).
Every chunk carries doc_id, title, section, classification (public < internal < confidential) for access control.
"""

import argparse
import csv
import logging

from langchain_core.documents import Document

from supplykb.chunking import chunk_markdown, contextual_header
from supplykb.config import get_settings
from supplykb.loaders import IMAGE_MARKER, LoadedDocument, load_document
from supplykb.retrieval import COLLECTIONS, get_client, get_store

log = logging.getLogger(__name__)
SUPPORTED = (".pdf", ".docx", ".html", ".htm", ".md", ".txt")
CSV_CLASSIFICATION = "internal"


def load_all() -> list[LoadedDocument]:
    s = get_settings()
    image_dir = s.extracted_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    return [load_document(p, image_dir) for p in sorted(s.data_dir.iterdir()) if p.suffix.lower() in SUPPORTED]


def document_chunks(doc: LoadedDocument, captions: dict[str, str]) -> list[Document]:
    s = get_settings()
    base = {"doc_id": doc.doc_id, "title": doc.title, "classification": doc.classification,
            "source_file": doc.path.name, "revision": str(doc.meta.get("revision", ""))}
    out: list[Document] = []
    for c in chunk_markdown(doc.markdown, s.chunk_size, s.chunk_overlap, s.table_max_chars):
        path = [p for p in c.section_path if p != doc.title]
        section = path[-1] if path else "Overview"
        header = contextual_header(doc.title, doc.doc_id, c.section_path)
        text = IMAGE_MARKER.sub("", c.text).strip()
        for image_id in IMAGE_MARKER.findall(c.text):  # each figure becomes its own chunk
            img = next(i for i in doc.images if i["image_id"] == image_id)
            out.append(Document(page_content=f"{header}\n[Figure {image_id}] {captions.get(image_id, '')}",
                                metadata={**base, "section": section, "content_type": "image", "image_id": image_id,
                                          "image_path": img["path"].replace("\\", "/"), "page": img["page"] or 0},
                                id=f"{doc.doc_id}::{image_id}"))
        if text:
            out.append(Document(page_content=f"{header}\n{text}",
                                metadata={**base, "section": section, "content_type": c.content_type},
                                id=f"{doc.doc_id}::{len(out)}"))
    return out


def csv_chunks() -> list[Document]:
    path = get_settings().data_dir / "inventory_lots.csv"
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            text = (f"Inventory record {r['lot_id']}: {r['product']} at {r['site']}; {r['quantity_vials']} vials; expiry "
                    f"{r['expiry']}; storage {r['storage']}; status {r['status']}; temperature excursions {r['excursions']}")
            out.append(Document(page_content=text, id=f"INV::{r['lot_id']}", metadata={
                "doc_id": "INV-LOTS", "title": "Lot inventory", "section": r["lot_id"], "classification": CSV_CLASSIFICATION,
                "content_type": "record", "lot_id": r["lot_id"], "source_file": path.name, "revision": ""}))
    return out


def all_chunks(allow_vision: bool = True) -> list[Document]:
    from supplykb.vision import get_captions

    docs = load_all()
    captions = get_captions([i for d in docs for i in d.images], allow_model=allow_vision)
    return [c for d in docs for c in document_chunks(d, captions)] + csv_chunks()


def build_index(allow_vision: bool = True) -> dict:
    client = get_client()
    if "documents" in {c.name for c in client.list_collections()}:
        client.delete_collection("documents")
    chunks = all_chunks(allow_vision)
    get_store("documents").add_documents(chunks, ids=[c.id for c in chunks])
    by_type: dict[str, int] = {}
    for c in chunks:
        by_type[c.metadata["content_type"]] = by_type.get(c.metadata["content_type"], 0) + 1
    return {"chunks": len(chunks), "by_type": by_type}


def index_exists() -> bool:
    client = get_client()
    if not set(COLLECTIONS) <= {c.name for c in client.list_collections()}:
        return False
    col = client.get_collection("documents")
    return col.count() > 0 and (col.metadata or {}).get("index_fingerprint") == get_settings().index_fingerprint


def ensure_index() -> None:
    if not index_exists():
        build_index()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-vision", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    print(build_index(allow_vision=not args.no_vision))
