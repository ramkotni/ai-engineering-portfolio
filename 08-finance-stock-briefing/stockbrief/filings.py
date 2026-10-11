"""SEC filing extraction: EDGAR HTML (10-K, 10-Q, 8-K) -> the sections an advisor needs, as Markdown.

Real filings are noisy HTML (inline XBRL). The same parser handles the synthetic filings and live EDGAR documents:

  1. Hidden XBRL headers, scripts and display:none blocks are removed; lxml parses multi-MB files in seconds.
  2. Leaf blocks (paragraphs, divs without block children, tables) are read in document order. Text is joined
     WITHOUT separators across inline spans, because filings split words over styled spans ("RIS" + "K FACTORS").
  3. Tables: "$" cells dropped, ")" and "%" cells glued to the number before them, empty spacer cells removed ->
     Markdown pipe tables. Single-column layout tables are treated as text.
  4. Item headings: "ITEM 1A. RISK FACTORS" (number + title). Bare "Item 1A" lines are running page headers and
     "Table of Contents" back-links / page numbers are page furniture - all dropped.
  5. The table of contents also lists every item. For each item we keep the occurrence followed by the LONGEST
     section, which is the real one (the TOC entry is followed by the next TOC line).
  6. 10-Q items repeat across parts (Part I Item 2 = MD&A, Part II Item 1A = risk-factor updates), so 10-Q keys are
     part-qualified: "I-2", "II-1A".
  7. 8-K: short documents - kept whole.
"""

import re
import warnings
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

ITEM = re.compile(r"^item\s*(\d{1,2}[a-c]?)\s*[.:\-–—]?\s*(.*)$", re.IGNORECASE)
PART = re.compile(r"^part\s+(iv|i{1,3})\b", re.IGNORECASE)
NOISE = re.compile(r"^(table of contents|index|\d{1,3}|page \d+|item\s*\d{1,2}[a-c]?(\s*[,&]\s*\d{1,2}[a-c]?)*)$", re.IGNORECASE)
SECTIONS = {
    "10-K": {"1": "Business", "1A": "Risk Factors", "7": "Management's Discussion and Analysis"},
    "10-Q": {"I-2": "Management's Discussion and Analysis", "II-1A": "Risk Factors"},
}
SECTION_GROUP = {"1": "business", "1A": "risks", "II-1A": "risks", "7": "mdna", "I-2": "mdna", "8-K": "events"}


@dataclass
class Filing:
    ticker: str
    form: str
    filed: str
    period: str
    source: str                                   # "synthetic" | "SEC EDGAR"
    url: str
    sections: dict[str, tuple[str, str]] = field(default_factory=dict)   # key -> (title, markdown)
    stats: dict = field(default_factory=dict)

    @property
    def doc_id(self) -> str:
        return f"{self.ticker}-{self.form}-{self.filed}"


def _norm(text: str) -> str:
    return " ".join(text.replace("\xa0", " ").split())


def _table_rows(table) -> list[list[str]]:
    rows = []
    for tr in table.find_all("tr"):
        cells = []
        for td in tr.find_all(["td", "th"]):
            c = _norm(td.get_text("", strip=False))
            if not c or c == "$":
                continue
            if c in (")", "%", ")%", "%)") and cells:
                cells[-1] += c
                continue
            cells.append(c.replace("|", "/"))
        if cells:
            rows.append(cells)
    return rows


def table_md(rows: list[list[str]]) -> str:
    width = max(map(len, rows))
    rows = [r + [""] * (width - len(r)) for r in rows]
    return "\n".join(["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width] + ["| " + " | ".join(r) + " |" for r in rows[1:]])


def html_blocks(html: str) -> list[tuple[str, object]]:
    soup = BeautifulSoup(html, "lxml")
    for el in soup(["script", "style", "head"]):
        el.decompose()
    for el in soup.find_all(style=re.compile(r"display:\s*none", re.IGNORECASE)):
        el.decompose()
    for el in soup.find_all(re.compile(r"^ix:header$")):
        el.decompose()
    blocks: list[tuple[str, object]] = []
    root = soup.body or soup
    for el in root.find_all(["p", "div", "table", "li", "h1", "h2", "h3", "h4"]):
        if el.name == "table":
            if el.find_parent("table"):
                continue
            rows = _table_rows(el)
            if rows and max(map(len, rows)) == 1:          # layout table holding prose
                blocks += [("text", r[0]) for r in rows]
            elif rows:
                blocks.append(("table", rows))
            continue
        if el.find_parent("table") or el.find(["p", "div", "table", "li"]):
            continue                                       # only leaf blocks outside tables
        text = _norm(el.get_text("", strip=False))
        if text:
            blocks.append(("text", text))
    return blocks


def split_sections(blocks: list[tuple[str, object]], form: str) -> tuple[dict[str, tuple[str, list]], dict]:
    part = "I"
    heads: list[tuple[int, str, str]] = []
    for i, (kind, content) in enumerate(blocks):
        if kind != "text" or len(content) > 200:
            continue
        p = PART.match(content)
        if p and len(content) < 80:
            part = p.group(1).upper()
            continue
        m = ITEM.match(content)
        if m and m.group(2).strip(" .:-"):                 # number AND title -> heading (bare "Item 1A" is a running header)
            key = m.group(1).upper()
            heads.append((i, f"{part}-{key}" if form == "10-Q" else key, m.group(2).strip(" .:-")))
    best: dict[str, tuple[int, int, int, str]] = {}
    for n, (i, key, title) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(blocks)
        size = sum(len(str(c)) for _, c in blocks[i + 1:end])
        if key not in best or size > best[key][2]:
            best[key] = (i, end, size, title)
    stats = {"blocks": len(blocks), "item_headings_found": len(heads), "toc_or_duplicate_headings_skipped": len(heads) - len(best)}
    return {key: (title, blocks[i + 1:end]) for key, (i, end, _, title) in best.items()}, stats


def section_markdown(title: str, blocks: list[tuple[str, object]], max_chars: int | None = None) -> tuple[str, int]:
    parts, removed, size = [], 0, 0
    for kind, content in blocks:
        if kind == "text" and (NOISE.match(content) or PART.match(content)):
            removed += 1
            continue
        piece = table_md(content) if kind == "table" else content
        if max_chars and size + len(piece) > max_chars:
            break
        parts.append(piece)
        size += len(piece)
    return f"## {title}\n\n" + "\n\n".join(parts), removed


def parse_filing(html: str, ticker: str, form: str, filed: str, period: str, source: str, url: str,
                 max_chars: int | None = None) -> Filing:
    blocks = html_blocks(html)
    filing = Filing(ticker, form, filed, period, source, url)
    if form.startswith("8-K"):
        md, removed = section_markdown(f"Form 8-K current report ({filed})", blocks, max_chars or 8000)
        filing.sections["8-K"] = (f"Current report {filed}", md)
        filing.stats = {"blocks": len(blocks), "noise_blocks_removed": removed}
        return filing
    sections, stats = split_sections(blocks, form)
    removed_total = 0
    for key, title in SECTIONS.get(form, {}).items():
        if key in sections:
            _heading, body = sections[key]
            md, removed = section_markdown(f"Item {key.split('-')[-1]}. {title}", body, max_chars)
            filing.sections[key] = (title, md)
            removed_total += removed
    filing.stats = {**stats, "noise_blocks_removed": removed_total, "sections_kept": sorted(filing.sections)}
    return filing
