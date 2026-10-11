"""Extraction: PDF, Word, HTML, Markdown and CSV -> normalised Markdown + metadata, with IMAGE EXTRACTION.

Every format becomes Markdown so one structure-aware chunker handles all of them:
  .pdf   pdfplumber for text and ruled tables (reading order kept by cutting each page into strips around
         tables and images; headings recovered from font size) + PyMuPDF for embedded images
  .docx  python-docx: heading styles -> #, tables -> pipe tables, inline pictures extracted in body order
  .html  BeautifulSoup: headings, paragraphs, lists, tables
  .md    as is
  .csv   one record per row (handled in ingest)

Each extracted image is saved to data/extracted/images/<image_id>.png and replaced in the text by a
marker line  [[IMAGE:<image_id>]]  at the position where it appears, so its caption becomes a chunk under
the right section heading.
"""

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

IMAGE_MARKER = re.compile(r"\[\[IMAGE:([\w.-]+)\]\]")
_META_KEYS = {"document id": "doc_id", "revision": "revision", "owner": "owner", "classification": "classification"}
MIN_IMAGE_PIXELS = 120 * 120  # ignore logos / bullets


@dataclass
class LoadedDocument:
    path: Path
    markdown: str
    meta: dict = field(default_factory=dict)
    images: list[dict] = field(default_factory=list)   # {"image_id", "path", "page"}

    @property
    def doc_id(self) -> str:
        return str(self.meta.get("doc_id") or self.path.stem)

    @property
    def title(self) -> str:
        return str(self.meta.get("title") or self.path.stem)

    @property
    def classification(self) -> str:
        return str(self.meta.get("classification", "internal")).lower()


def parse_meta_line(text: str, meta: dict) -> bool:
    """'Document ID: X | Revision: 6 | Classification: Internal' -> meta. Returns True if it was a meta line."""
    found = False
    for part in text.split("|"):
        key, _, value = part.partition(":")
        if key.strip().lower() in _META_KEYS and value.strip():
            meta[_META_KEYS[key.strip().lower()]] = value.strip()
            found = True
    return found


def table_md(rows: list[list]) -> str:
    rows = [[" ".join(str(c or "").split()).replace("|", "/") for c in r] for r in rows if r and any(r)]
    if not rows:
        return ""
    width = max(map(len, rows))
    rows = [r + [""] * (width - len(r)) for r in rows]
    return "\n".join(["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width] + ["| " + " | ".join(r) + " |" for r in rows[1:]])


# ---------------------------------------------------------------- PDF
def load_pdf(path: Path, image_dir: Path) -> LoadedDocument:
    import pdfplumber
    import pymupdf

    meta: dict = {}
    images: list[dict] = []
    segments: list[tuple[str, object]] = []
    mu = pymupdf.open(str(path))
    with pdfplumber.open(str(path)) as pdf:
        if (pdf.metadata or {}).get("Title"):
            meta["title"] = pdf.metadata["Title"]
        for pno, page in enumerate(pdf.pages):
            blocks = [("table", t.bbox[1], t.bbox[3], t) for t in page.find_tables()]
            for n, info in enumerate(mu[pno].get_images(full=True), start=1):
                xref = info[0]
                img = mu.extract_image(xref)
                if img["width"] * img["height"] < MIN_IMAGE_PIXELS:
                    continue
                rects = mu[pno].get_image_rects(xref)
                top, bottom = (rects[0].y0, rects[0].y1) if rects else (page.height, page.height)
                image_id = f"{path.stem.split('_')[0]}_p{pno + 1}_img{n}"
                out = image_dir / f"{image_id}.{img['ext']}"
                out.write_bytes(img["image"])
                images.append({"image_id": image_id, "path": str(out), "page": pno + 1})
                blocks.append(("image", top, bottom, image_id))
            y = 0.0
            for kind, top, bottom, obj in sorted(blocks, key=lambda b: b[1]):
                segments.append(("lines", _lines(page.crop((0, y, page.width, max(y, top))))))
                segments.append(("table", table_md(obj.extract())) if kind == "table" else ("image", obj))
                y = bottom
            segments.append(("lines", _lines(page.crop((0, min(y, page.height), page.width, page.height)))))

    sizes = [s for kind, lines in segments if kind == "lines" for _, s in lines]
    body = statistics.median(sizes) if sizes else 0
    heading_sizes = sorted({round(s, 1) for s in sizes if s >= body * 1.15}, reverse=True)[:3]
    parts: list[str] = []
    for kind, content in segments:
        if kind == "table":
            parts.append(content)
        elif kind == "image":
            parts.append(f"[[IMAGE:{content}]]")
        else:
            for text, size in content:
                if round(size, 1) in heading_sizes:
                    level = heading_sizes.index(round(size, 1)) + 1
                    parts.append(f"{'#' * level} {text}")
                    if level == 1:
                        meta.setdefault("title", text)
                elif parse_meta_line(text, meta):
                    continue
                elif parts and not parts[-1].startswith(("#", "|", "[[")) and not parts[-1].rstrip().endswith((".", ":", ";", "?", "!")):
                    parts[-1] += " " + text
                else:
                    parts.append(text)
    return LoadedDocument(path, "\n\n".join(p for p in parts if p), meta, images)


def _lines(region) -> list[tuple[str, float]]:
    out = []
    for line in region.extract_text_lines(return_chars=True):
        text = " ".join(line["text"].split())
        if text:
            out.append((text, max(c["size"] for c in line["chars"])))
    return out


# ---------------------------------------------------------------- Word
def load_docx(path: Path, image_dir: Path) -> LoadedDocument:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = docx.Document(str(path))
    meta: dict = {"title": d.core_properties.title} if d.core_properties.title else {}
    parts: list[str] = []
    images: list[dict] = []
    for child in d.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "tbl":
            t = Table(child, d)
            parts.append(table_md([[c.text for c in row.cells] for row in t.rows]))
            continue
        if tag != "p":
            continue
        p = Paragraph(child, d)
        for blip in child.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
            rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
            part = d.part.related_parts[rid]
            image_id = f"{path.stem.split('_')[0]}_img{len(images) + 1}"
            out = image_dir / f"{image_id}.{part.partname.ext}"
            out.write_bytes(part.blob)
            images.append({"image_id": image_id, "path": str(out), "page": None})
            parts.append(f"[[IMAGE:{image_id}]]")
        text = p.text.strip()
        if not text:
            continue
        style = (p.style.name or "").lower() if p.style is not None else ""
        if style == "title" or style.startswith("heading"):
            level = 1 if style == "title" else min(int(re.sub(r"\D", "", style) or 1), 3)
            parts.append(f"{'#' * level} {text}")
            if level == 1:
                meta.setdefault("title", text)
        elif not parse_meta_line(text, meta):
            parts.append(text)
    return LoadedDocument(path, "\n\n".join(parts), meta, images)


# ---------------------------------------------------------------- HTML + Markdown
def load_html(path: Path) -> LoadedDocument:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    meta = {"title": soup.title.get_text(strip=True)} if soup.title else {}
    parts: list[str] = []
    for el in soup.body.find_all(["h1", "h2", "h3", "p", "ul", "ol", "table"]):
        if el.name not in ("ul", "ol", "table") and el.find_parent(["table", "ul", "ol"]):
            continue
        text = " ".join(el.get_text(" ", strip=True).split())
        if el.name in ("h1", "h2", "h3"):
            parts.append("#" * int(el.name[1]) + " " + text)
        elif el.name == "table":
            parts.append(table_md([[c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])] for tr in el.find_all("tr")]))
        elif el.name in ("ul", "ol"):
            parts.append("\n".join(f"- {' '.join(li.get_text(' ', strip=True).split())}" for li in el.find_all("li")))
        elif text and not parse_meta_line(text, meta):
            parts.append(text)
    return LoadedDocument(path, "\n\n".join(parts), meta)


def load_markdown(path: Path) -> LoadedDocument:
    meta: dict = {}
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if parse_meta_line(line, meta):
            continue
        if line.startswith("# ") and "title" not in meta:
            meta["title"] = line[2:].strip()
        lines.append(line)
    return LoadedDocument(path, "\n".join(lines), meta)


def load_document(path: Path, image_dir: Path) -> LoadedDocument:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path, image_dir)
    if suffix == ".docx":
        return load_docx(path, image_dir)
    if suffix in (".html", ".htm"):
        return load_html(path)
    if suffix in (".md", ".txt"):
        return load_markdown(path)
    raise ValueError(f"Unsupported: {path}")
