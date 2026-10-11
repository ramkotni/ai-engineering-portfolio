"""The complex-PDF extraction contract: each layout feature of the guideline PDF is handled correctly."""

from pathlib import Path

import pytest

from medbrief.loaders import load_document

RAW = Path("data/raw")


@pytest.fixture(scope="module")
def pdf(tmp_path_factory):
    return load_document(RAW / "CARD-GL-2026_hfref_guideline_summary.pdf", tmp_path_factory.mktemp("img"))


def test_metadata_and_title(pdf):
    assert pdf.meta["doc_id"] == "CARD-GL-2026" and pdf.classification == "public" and pdf.meta["revision"] == "3"
    assert pdf.markdown.startswith("# Heart Failure with Reduced Ejection Fraction (HFrEF): Guideline Summary 2026")


def test_running_header_and_footer_removed(pdf):
    assert pdf.stats["header_footer_lines_removed"] == 2 * pdf.stats["pages"]
    assert "NOT FOR CLINICAL USE" not in pdf.markdown and "Page 2 of" not in pdf.markdown and "CARD-GL-2026 Rev 3" not in pdf.markdown


def test_two_column_reading_order(pdf):
    md = pdf.markdown
    assert pdf.stats["two_column_blocks"] >= 3
    # left column (Definition) is read completely before the right column (Diagnosis)
    assert md.index("value-based care programs") < md.index("### 2. Diagnosis") < md.index("NT-proBNP above 125 pg/mL")
    # a right-column paragraph is complete, not interleaved with the left column
    assert "Rapid sequencing - all four pillars within six weeks and dose titration every two weeks - is preferred" in md
    # the table caption comes after both columns and directly before its table
    assert md.index("Table 1 lists recommended agents") < md.index("Table 1. Recommended GDMT for HFrEF") < md.index("| Drug class |")


def test_table_continued_across_page_break_is_merged(pdf):
    assert pdf.stats["tables_merged_across_pages"] == 1
    table = [ln for ln in pdf.markdown.splitlines() if ln.startswith("| ")]
    gdmt = table[: table.index(next(ln for ln in table if ln.startswith("| Measure")))]
    assert len(gdmt) == 12                       # header + 11 drug rows, header not repeated
    assert sum(ln.startswith("| Drug class") for ln in gdmt) == 1
    assert "| IV iron | ferric carboxymaltose |" in pdf.markdown and "(continued)" not in pdf.markdown


def test_images_extracted_at_their_position_with_captions(pdf):
    assert [i["page"] for i in pdf.images] == [2, 3]
    assert all(Path(i["path"]).stat().st_size > 10_000 for i in pdf.images)
    md = pdf.markdown
    assert md.index("## 4. Device Therapy") < md.index("[[IMAGE:CARD-GL-2026_p2_img1]]") < md.index("## 5. Emerging Therapies")
    assert pdf.images[0]["caption_hint"].startswith("Figure 1. HFrEF treatment algorithm")


def test_footnotes_tagged(pdf):
    assert pdf.stats["footnotes"] == 2 and "Footnote: a. Doses are examples" in pdf.markdown


def test_docx_and_html(tmp_path):
    d = load_document(RAW / "STRAT-2026_cardiometabolic_service_line.docx", tmp_path)
    assert d.classification == "internal" and len(d.images) == 1 and "| Pentara Health AI |" in d.markdown
    h = load_document(RAW / "DM-GL-2026_type2_diabetes_care_summary.html", tmp_path)
    assert h.meta["doc_id"] == "DM-GL-2026" and "| SGLT2 inhibitor | Intermediate | Loss |" in h.markdown


def test_chunks_carry_condition_and_types(chunks):
    types = {c.metadata["content_type"] for c in chunks}
    assert {"text", "table", "image", "record"} <= types
    by_doc = {c.metadata["doc_id"]: c.metadata["condition"] for c in chunks if c.metadata["doc_id"] in ("CARD-GL-2026", "DM-GL-2026")}
    assert by_doc == {"CARD-GL-2026": "hfref", "DM-GL-2026": "t2d"}
    strat = {c.metadata["condition"] for c in chunks if c.metadata["doc_id"] == "STRAT-2026"}
    assert {"hfref", "t2d"} <= strat
    table = next(c for c in chunks if "| ARNI |" in c.page_content)
    assert "| IV iron |" in table.page_content       # the merged table stays one chunk
