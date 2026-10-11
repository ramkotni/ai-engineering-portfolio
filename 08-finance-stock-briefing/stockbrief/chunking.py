"""Structure-aware chunking of normalised Markdown.

Rules (in priority order):
  1. Never cross a section boundary - a chunk belongs to exactly one heading path
     ("Title > Section > Subsection"), which is also stored as metadata and cited.
  2. Never split a table that fits in `table_max_chars`; larger tables are split by rows
     and every piece repeats the header row, so each chunk is a readable table.
  3. Pack paragraphs, lists and steps of a section together up to `chunk_size` characters;
     an oversized paragraph is split recursively (paragraph -> line -> sentence -> word)
     with `chunk_overlap`.
  4. Prefix every chunk with a contextual header (document title, ID, section path) so the
     embedding and BM25 both "know" where the text came from.
"""

import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNKER_VERSION = "2"  # bump when chunking logic changes -> forces an index rebuild

_HEADING = re.compile(r"^(#{1,3})\s+(.*\S)\s*$")
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")


@dataclass
class Block:
    kind: str          # "text" | "table"
    text: str
    section_path: tuple[str, ...]


@dataclass
class Chunk:
    text: str          # body without the contextual header
    section_path: tuple[str, ...]
    content_type: str  # "text" | "table" | "mixed"


def parse_blocks(markdown: str) -> list[Block]:
    """Split Markdown into text/table blocks, each tagged with its heading path."""
    blocks: list[Block] = []
    path: list[str] = []
    buf: list[str] = []
    in_table = False

    def flush() -> None:
        nonlocal buf
        text = "\n".join(buf).strip()
        if text:
            blocks.append(Block("table" if in_table else "text", text, tuple(path)))
        buf = []

    for line in markdown.splitlines():
        heading = _HEADING.match(line)
        if heading:
            flush()
            in_table = False
            level = len(heading.group(1))
            path[:] = path[: level - 1] + [heading.group(2)]
            continue
        is_table = bool(_TABLE_LINE.match(line))
        if is_table != in_table:
            flush()
            in_table = is_table
        if not is_table and not line.strip():
            flush()  # blank line ends a paragraph / list
            continue
        buf.append(line)
    flush()
    return blocks


def split_table(table: str, max_chars: int) -> list[str]:
    """Split an oversized Markdown table by rows, repeating the header + separator rows."""
    lines = table.splitlines()
    header, rows = lines[:2], lines[2:]
    pieces, current = [], list(header)
    for row in rows:
        if len("\n".join(current + [row])) > max_chars and len(current) > 2:
            pieces.append("\n".join(current))
            current = list(header)
        current.append(row)
    pieces.append("\n".join(current))
    return pieces


def chunk_markdown(markdown: str, chunk_size: int, chunk_overlap: int, table_max_chars: int) -> list[Chunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks: list[Chunk] = []
    pending: list[Block] = []

    def emit() -> None:
        if pending:
            kinds = {b.kind for b in pending}
            chunks.append(Chunk("\n\n".join(b.text for b in pending), pending[0].section_path,
                                kinds.pop() if len(kinds) == 1 else "mixed"))
            pending.clear()

    for block in parse_blocks(markdown):
        if pending and block.section_path != pending[0].section_path:
            emit()  # rule 1: section boundary

        if block.kind == "table":
            pieces = [block.text] if len(block.text) <= table_max_chars else split_table(block.text, table_max_chars)
            if len(pieces) > 1:
                emit()
                chunks += [Chunk(p, block.section_path, "table") for p in pieces]
                continue
            block_text = pieces[0]
        else:
            block_text = block.text

        if len(block_text) > chunk_size and block.kind == "text":
            emit()
            chunks += [Chunk(t, block.section_path, "text") for t in splitter.split_text(block_text)]
            continue

        current = sum(len(b.text) + 2 for b in pending)
        if pending and current + len(block_text) > max(chunk_size, table_max_chars if block.kind == "table" else 0):
            emit()
        pending.append(Block(block.kind, block_text, block.section_path))
    emit()
    return chunks


def contextual_header(title: str, doc_id: str, section_path: tuple[str, ...]) -> str:
    # The H1 usually repeats the title; drop it from the path to keep the header short.
    path = [p for p in section_path if p != title]
    return f"{title} ({doc_id})" + (" > " + " > ".join(path) if path else "")
