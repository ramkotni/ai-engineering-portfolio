"""Ingestion: complex PDF / Word / HTML + extracted figures + trial registry -> chunks -> nomic-embed-text -> ChromaDB.

    python -m medbrief.ingest            # uses cached figure captions; captions new figures if the vision model is up
    python -m medbrief.ingest --no-vision

Also writes the extraction output for review (committed): data/extracted/markdown/<doc_id>.md and
data/extracted/extraction_report.json (what the extractor did per document).

Chunk types (metadata content_type): text | table | mixed | image (figure caption) | record (registry row).
Every chunk carries doc_id, title, section, condition (hfref | t2d | all) and classification (public | internal).
"""

import argparse
import json
import logging
import re

from langchain_core.documents import Document

from medbrief.chunking import chunk_markdown, contextual_header
from medbrief.conditions import CATALOGUE, tag_condition
from medbrief.config import get_settings
from medbrief.loaders import IMAGE_MARKER, LoadedDocument, load_document
from medbrief.retrieval import COLLECTIONS, get_client, get_store

log = logging.getLogger(__name__)
SUPPORTED = (".pdf", ".docx", ".html", ".htm", ".md")
DOC_CONDITION = {doc: c.key for c in CATALOGUE.values() for doc in c.guideline_docs}   # single-condition documents


def load_all() -> list[LoadedDocument]:
    s = get_settings()
    image_dir = s.extracted_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    return [load_document(p, image_dir) for p in sorted(s.data_dir.iterdir()) if p.suffix.lower() in SUPPORTED]


DRUG_LIKE = re.compile(r"\b[A-Za-z]{5,}(?:zide|pril|sartan|olol|azine|flozin|glutide|tide|mab|nib|statin|parin|gliptin|formin|lone|tone)\b",
                       re.IGNORECASE)


def unverified_terms(caption: str, document_text: str) -> list[str]:
    """Drug-like names in a vision caption that occur nowhere else in the source document. Vision models misread
    small text (e.g. 'Hydralazine' -> 'Hydrochlorothiazide'); flagged terms are shown to the writer and the reader."""
    doc = document_text.lower()
    return sorted({w.lower(): w for w in DRUG_LIKE.findall(caption) if w.lower() not in doc}.values())


def document_chunks(doc: LoadedDocument, captions: dict[str, str]) -> list[Document]:
    s = get_settings()
    base = {"doc_id": doc.doc_id, "title": doc.title, "classification": doc.classification,
            "source_file": doc.path.name, "revision": str(doc.meta.get("revision", ""))}
    out: list[Document] = []
    for c in chunk_markdown(doc.markdown, s.chunk_size, s.chunk_overlap, s.table_max_chars):
        path = [p for p in c.section_path if p != doc.title]
        section = path[-1] if path else "Overview"
        header = contextual_header(doc.title, doc.doc_id, c.section_path)
        condition = DOC_CONDITION.get(doc.doc_id) or tag_condition(section + " " + c.text)
        text = IMAGE_MARKER.sub("", c.text).strip()
        for image_id in IMAGE_MARKER.findall(c.text):  # each figure becomes its own chunk
            img = next(i for i in doc.images if i["image_id"] == image_id)
            caption = captions.get(image_id, "")
            flagged = unverified_terms(caption, doc.markdown)
            warning = f"\n[Vision transcription - terms not found elsewhere in the document, verify: {', '.join(flagged)}]" if flagged else ""
            out.append(Document(
                page_content=f"{header}\n[Figure {image_id}] {img.get('caption_hint', '')}\n{caption}{warning}".strip(),
                metadata={**base, "section": section, "condition": condition, "content_type": "image", "image_id": image_id,
                          "image_path": _rel(img["path"]), "page": img["page"] or 0, "unverified_terms": ", ".join(flagged)},
                id=f"{doc.doc_id}::{image_id}"))
        if text:
            out.append(Document(page_content=f"{header}\n{text}",
                                metadata={**base, "section": section, "condition": condition, "content_type": c.content_type},
                                id=f"{doc.doc_id}::{len(out)}"))
    return out


def registry_chunks() -> list[Document]:
    from medbrief.trials import synthetic_trials

    out = []
    for cond in CATALOGUE.values():
        for t in synthetic_trials(cond):
            out.append(Document(page_content=t.as_text(), id=f"REG::{t.trial_id}", metadata={
                "doc_id": "REG-2026", "title": "Synthetic trial registry", "section": t.trial_id, "condition": cond.key,
                "classification": "public", "content_type": "record", "trial_id": t.trial_id, "source_file": "pipeline_trials.csv",
                "revision": ""}))
    return out


def _rel(path: str) -> str:
    p = path.replace("\\", "/")
    return p[p.index("data/"):] if "data/" in p else p


def all_chunks(allow_vision: bool = True, docs: list[LoadedDocument] | None = None) -> list[Document]:
    from medbrief.vision import get_captions

    docs = docs or load_all()
    captions = get_captions([i for d in docs for i in d.images], allow_model=allow_vision)
    return [c for d in docs for c in document_chunks(d, captions)] + registry_chunks()


def write_extraction_artifacts(docs: list[LoadedDocument]) -> dict:
    s = get_settings()
    md_dir = s.extracted_dir / "markdown"
    md_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for d in docs:
        (md_dir / f"{d.doc_id}.md").write_text(d.markdown + "\n", encoding="utf-8")
        report[d.doc_id] = {"file": d.path.name, "title": d.title, "classification": d.classification, **d.stats,
                            "images": [{"image_id": i["image_id"], "page": i["page"], "caption_hint": i.get("caption_hint", "")} for i in d.images]}
    (s.extracted_dir / "extraction_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def build_index(allow_vision: bool = True) -> dict:
    client = get_client()
    if "documents" in {c.name for c in client.list_collections()}:
        client.delete_collection("documents")
    docs = load_all()
    write_extraction_artifacts(docs)
    chunks = all_chunks(allow_vision, docs)
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
