from pathlib import Path

import pytest

from plant_assist.chunking import (
    chunk_markdown,
    contextual_header,
    parse_blocks,
    split_table,
)
from plant_assist.loaders import load_document

FIXTURES = Path(__file__).parent / "fixtures"
DOCX = Path(__file__).parent.parent / "data" / "docs" / "maintenance" / "MM-HP-200-TS_torque_specs.docx"

MD = """# Press Manual
## Overview
The press has a 30 kW pump.

## Torque Specifications
Use a calibrated wrench.

| Fastener | Torque |
|---|---|
| Gland bolts | 210 |
| Mount bolts | 650 |

### Notes
Re-check after 24 h.
"""


def test_blocks_track_heading_path_and_tables():
    blocks = parse_blocks(MD)
    assert [(b.kind, b.section_path[-1]) for b in blocks] == [
        ("text", "Overview"), ("text", "Torque Specifications"), ("table", "Torque Specifications"), ("text", "Notes"),
    ]
    assert blocks[-1].section_path == ("Press Manual", "Torque Specifications", "Notes")


def test_chunks_never_cross_sections_and_keep_tables_whole():
    chunks = chunk_markdown(MD, chunk_size=900, chunk_overlap=100, table_max_chars=2500)
    assert [c.section_path[-1] for c in chunks] == ["Overview", "Torque Specifications", "Notes"]
    torque = chunks[1]
    assert torque.content_type == "mixed" and "| Gland bolts | 210 |" in torque.text and "| Mount bolts | 650 |" in torque.text


def test_large_table_split_by_rows_repeats_header():
    table = "| Part | Torque |\n|---|---|\n" + "\n".join(f"| bolt-{i} | {i * 10} |" for i in range(60))
    pieces = split_table(table, max_chars=300)
    assert len(pieces) > 1
    assert all(p.startswith("| Part | Torque |\n|---|---|") for p in pieces)
    assert sum(p.count("| bolt-") for p in pieces) == 60  # no row lost or duplicated


def test_long_paragraph_is_split_with_size_limit():
    long_text = "## Section\n" + " ".join(f"Sentence number {i} about hydraulic maintenance." for i in range(80))
    chunks = chunk_markdown(long_text, chunk_size=400, chunk_overlap=50, table_max_chars=2500)
    assert len(chunks) > 1 and all(len(c.text) <= 400 for c in chunks)


def test_contextual_header_drops_repeated_title():
    assert contextual_header("Press Manual", "MM-1", ("Press Manual", "Torque")) == "Press Manual (MM-1) > Torque"


@pytest.mark.parametrize("path", [DOCX, FIXTURES / "torque_specs.pdf"])
def test_docx_and_pdf_extract_same_structure(path):
    doc = load_document(path)
    assert doc.doc_id == "MM-HP-200-TS" and doc.meta["revision"] == "2"
    chunks = chunk_markdown(doc.markdown, 900, 120, 2500)
    sections = [c.section_path[-1] for c in chunks]
    assert sections == ["Torque Specifications", "Fluid Specifications", "Escalation"]
    torque_table = chunks[0].text
    assert "| Gland retainer bolts | Main cylinder | M20 | 210 |" in torque_table
