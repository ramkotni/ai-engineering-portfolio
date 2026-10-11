"""Extraction for the payment sources.

  incidents.csv   -> one document per incident row (row = natural chunk: an incident is a unit of
                     evidence; splitting it would separate symptom, root cause and resolution)
  reports/*.html  -> normalised Markdown (headings, paragraphs, lists, tables) -> structure-aware chunks
  *.md            -> business rules / runbook -> structure-aware chunks
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup


@dataclass
class LoadedDocument:
    path: Path
    markdown: str
    meta: dict = field(default_factory=dict)

    @property
    def doc_id(self) -> str:
        return str(self.meta.get("doc_id") or self.path.stem)

    @property
    def title(self) -> str:
        return str(self.meta.get("title") or self.path.stem)


def load_incidents(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["amount_usd"] = float(r["amount_usd"])
        r["resolution_time_hours"] = float(r["resolution_time_hours"])
        r["payments_affected"] = int(r["payments_affected"])
    return rows


def incident_text(r: dict) -> str:
    """Render a CSV row as text for embedding + BM25 (labels help both)."""
    return (
        f"{r['incident_id']} | {r['date']} | {r['system']} | {r['payment_type']} | {r['severity']} | {r['failure_category']}\n"
        f"Title: {r['title']}\n"
        f"Symptom: {r['description']}\n"
        f"Root cause: {r['root_cause']}\n"
        f"Resolution: {r['resolution']}\n"
        f"Amount: ${r['amount_usd']:,.2f} | Payments affected: {r['payments_affected']} | "
        f"Resolution time: {r['resolution_time_hours']} h | Detected by: {r['detected_by']} | Status: {r['status']}"
    )


def _table_md(table) -> str:
    rows = [[" ".join(c.get_text(" ", strip=True).split()) for c in tr.find_all(["th", "td"])] for tr in table.find_all("tr")]
    rows = [r for r in rows if r]
    if not rows:
        return ""
    width = max(map(len, rows))
    rows = [r + [""] * (width - len(r)) for r in rows]
    return "\n".join(["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width] + ["| " + " | ".join(r) + " |" for r in rows[1:]])


def load_html(path: Path) -> LoadedDocument:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    meta = {"title": soup.title.get_text(strip=True) if soup.title else path.stem}
    parts: list[str] = []
    for el in soup.body.find_all(["h1", "h2", "h3", "p", "ul", "ol", "table"], recursive=True):
        if el.find_parent(["table", "ul", "ol"]) is not None and el.name not in ("ul", "ol", "table"):
            continue
        text = " ".join(el.get_text(" ", strip=True).split())
        if el.name in ("h1", "h2", "h3"):
            parts.append("#" * int(el.name[1]) + " " + text)
        elif el.name == "table":
            parts.append(_table_md(el))
        elif el.name in ("ul", "ol"):
            parts.append("\n".join(f"- {' '.join(li.get_text(' ', strip=True).split())}" for li in el.find_all("li")))
        elif text:
            m = re.search(r"Document ID:\s*([\w-]+)", text)
            if m:
                meta["doc_id"] = m.group(1)
                continue
            parts.append(text)
    return LoadedDocument(path, "\n\n".join(parts), meta)


def load_markdown(path: Path) -> LoadedDocument:
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = re.search(r"Document ID:\s*([\w-]+)", text)
    if m:
        meta["doc_id"] = m.group(1)
    h1 = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if h1:
        meta["title"] = h1.group(1).strip()
    body = re.sub(r"^Document ID:.*$", "", text, flags=re.MULTILINE)
    return LoadedDocument(path, body, meta)
