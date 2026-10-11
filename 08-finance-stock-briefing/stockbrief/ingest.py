"""Filings ingestion: EDGAR-style HTML -> sections (Business, Risk Factors, MD&A, 8-K events) -> chunks -> ChromaDB.

    python -m stockbrief.ingest                  # index the synthetic filings (NWRB, HLXB)
    python -m stockbrief.ingest --live MSFT      # fetch + index a real company's latest 10-K, 10-Q and 8-Ks from SEC EDGAR

Live tickers are indexed on demand the first time they are briefed and cached (Chroma + data/cache). Each chunk
carries ticker, form, filed date, section_key (1, 1A, 7, I-2, II-1A, 8-K), section group (business | risks | mdna |
events) and source (synthetic | SEC EDGAR), so briefing sections retrieve only from the right filing items.
"""

import argparse
import json
import logging

from langchain_core.documents import Document

from stockbrief.chunking import chunk_markdown
from stockbrief.config import get_settings
from stockbrief.filings import SECTION_GROUP, Filing, parse_filing
from stockbrief.retrieval import COLLECTIONS, get_client, get_retrievers, get_store

log = logging.getLogger(__name__)


def synthetic_filings() -> list[Filing]:
    s = get_settings()
    out = []
    for d in sorted((s.data_dir / "filings").iterdir()):
        for f in json.loads((d / "filings_index.json").read_text(encoding="utf-8")):
            html = (d / f["file"]).read_text(encoding="utf-8")
            out.append(parse_filing(html, d.name, f["form"], f["filed"], f["period"], "synthetic", f"data/raw/filings/{d.name}/{f['file']}"))
    return out


def filing_chunks(filing: Filing) -> list[Document]:
    s = get_settings()
    out = []
    for key, (title, md) in filing.sections.items():
        label = f"{filing.ticker} {filing.form} filed {filing.filed}"
        for i, c in enumerate(chunk_markdown(md, s.chunk_size, s.chunk_overlap, s.table_max_chars)):
            out.append(Document(
                page_content=f"{label} > {title}\n{c.text}",
                metadata={"ticker": filing.ticker, "form": filing.form, "filed": filing.filed, "period": filing.period,
                          "doc_id": filing.doc_id, "title": label, "section_key": key, "section": title,
                          "group": SECTION_GROUP.get(key, "other"), "content_type": c.content_type, "source": filing.source, "url": filing.url},
                id=f"{filing.doc_id}::{key}::{i}"))
    return out


def all_synthetic_chunks() -> list[Document]:
    return [c for f in synthetic_filings() for c in filing_chunks(f)]


def build_index() -> dict:
    client = get_client()
    if "filings" in {c.name for c in client.list_collections()}:
        client.delete_collection("filings")
    get_retrievers.cache_clear()
    chunks = all_synthetic_chunks()
    get_store("filings").add_documents(chunks, ids=[c.id for c in chunks])
    return {"chunks": len(chunks), "tickers": sorted({c.metadata["ticker"] for c in chunks})}


def index_exists() -> bool:
    client = get_client()
    if not set(COLLECTIONS) <= {c.name for c in client.list_collections()}:
        return False
    col = client.get_collection("filings")
    return col.count() > 0 and (col.metadata or {}).get("index_fingerprint") == get_settings().index_fingerprint


def ensure_index() -> None:
    if not index_exists():
        build_index()


def ensure_live_ticker(company) -> dict:
    """Fetch and index a real company's latest 10-K, latest 10-Q and two latest 8-Ks (once; cached)."""
    from stockbrief.edgar import filing_html, recent_filings

    s = get_settings()
    marker = s.cache_dir / f"indexed_{company.ticker}.json"
    filings = recent_filings(company.cik, limit=12)
    wanted, seen = [], {"10-K": 0, "10-Q": 0, "8-K": 0}
    for f in filings:
        if seen[f["form"]] < (2 if f["form"] == "8-K" else 1):
            wanted.append(f)
            seen[f["form"]] += 1
    accessions = sorted(f["accession"] for f in wanted)
    if marker.exists() and json.loads(marker.read_text(encoding="utf-8")).get("accessions") == accessions:
        return {"ticker": company.ticker, "cached": True, "filings": wanted}
    chunks = []
    for f in wanted:
        parsed = parse_filing(filing_html(f), company.ticker, f["form"], f["filed"], f["period"], "SEC EDGAR", f["url"], s.live_section_chars)
        chunks += filing_chunks(parsed)
    store = get_store("filings")
    old = store.get(where={"ticker": company.ticker})
    if old["ids"]:
        store.delete(ids=old["ids"])
    store.add_documents(chunks, ids=[c.id for c in chunks])
    get_retrievers()["filings"]._corpus = None          # reload the in-memory corpus used for hybrid search
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(json.dumps({"accessions": accessions, "chunks": len(chunks)}), encoding="utf-8")
    return {"ticker": company.ticker, "cached": False, "chunks": len(chunks), "filings": wanted}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", metavar="TICKER")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if args.live:
        from stockbrief.companies import resolve

        ensure_index()
        company = resolve(args.live.upper(), "live")
        print(ensure_live_ticker(company) if company else f"Unknown ticker {args.live}")
    else:
        print(build_index())
