"""Generates the synthetic document set for the Supply Chain Knowledge Assistant.

    python data/generate_data.py

Outputs (committed) in data/raw/ - one per ingestion format, each with a classification level:
  SOP-CC-001_cold_chain_shipping.pdf     PDF  - headings, a ruled table, TWO embedded diagrams   (internal)
  DEV-2026-014_temperature_excursion.docx Word - timeline table + embedded temperature chart       (confidential)
  SUP-QUAL-2026_supplier_qualification.html HTML - supplier scorecard table                         (internal)
  GDP-POL-001_good_distribution_practice.md Markdown policy                                         (public)
  inventory_lots.csv                     CSV  - lot master data                                     (internal)

The diagrams contain text that appears nowhere else - so questions about them can only be answered
through image extraction + captioning. All products, lots, sites and suppliers are fictional.
"""

import csv
import io
import random
from pathlib import Path

import docx
import pymupdf
from docx.shared import Inches
from PIL import Image, ImageDraw, ImageFont

RAW = Path(__file__).parent / "raw"
random.seed(11)


def font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


# ---------------------------------------------------------------- images
def flowchart_png() -> bytes:
    """Temperature excursion decision flowchart (only source of these decision rules)."""
    img = Image.new("RGB", (1100, 760), "white")
    d = ImageDraw.Draw(img)
    f, fb = font(22), font(26)
    d.text((40, 20), "Figure 1 - Temperature Excursion Decision Flow (2-8 C products)", fill="black", font=fb)

    def box(x, y, w, h, text, fill):
        d.rounded_rectangle((x, y, x + w, y + h), radius=14, outline="black", width=3, fill=fill)
        for i, line in enumerate(text.split("\n")):
            d.text((x + 16, y + 12 + i * 28), line, fill="black", font=f)

    def arrow(x1, y1, x2, y2, label=""):
        d.line((x1, y1, x2, y2), fill="black", width=3)
        d.polygon([(x2, y2), (x2 - 8, y2 - 14), (x2 + 8, y2 - 14)] if y2 > y1 else [(x2, y2), (x2 - 14, y2 - 8), (x2 - 14, y2 + 8)], fill="black")
        if label:
            d.text(((x1 + x2) / 2 + 8, (y1 + y2) / 2 - 26), label, fill="black", font=f)

    box(330, 80, 440, 80, "Data logger alarm:\ntemperature outside 2-8 C", "#FFF2CC")
    arrow(550, 160, 550, 220)
    box(330, 220, 440, 80, "Excursion above 8 C for\nmore than 2 hours cumulative?", "#DDEBF7")
    arrow(330, 260, 190, 260)
    d.text((215, 228), "NO", fill="black", font=f)
    box(20, 330, 330, 110, "Release allowed:\nrecord in shipment file;\nno QA hold", "#E2F0D9")
    arrow(190, 260, 190, 330)
    arrow(770, 260, 900, 260)
    d.text((790, 228), "YES", fill="black", font=f)
    box(740, 330, 340, 110, "Quarantine lot (HOLD)\nnotify QA within 4 hours", "#F8CBAD")
    arrow(900, 260, 900, 330)
    arrow(910, 440, 910, 500)
    box(700, 500, 380, 110, "Any reading above 25 C\nor frozen (below 0 C)?", "#DDEBF7")
    arrow(890, 610, 890, 650)
    box(560, 650, 520, 80, "YES: reject lot | NO: stability review by QA", "#F8CBAD")
    return _png(img)


def network_png() -> bytes:
    """Distribution network diagram: lanes, transit times and packaging (only source of these lanes)."""
    img = Image.new("RGB", (1100, 620), "white")
    d = ImageDraw.Draw(img)
    f, fb = font(21), font(26)
    d.text((40, 20), "Figure 2 - Cold Chain Distribution Network", fill="black", font=fb)
    nodes = {"Manufacturing Site (Durham, NC)": (60, 120), "Central DC (Memphis, TN)": (420, 270),
             "West Hub (Reno, NV)": (800, 110), "East Hub (Allentown, PA)": (800, 430)}
    for name, (x, y) in nodes.items():
        d.rounded_rectangle((x, y, x + 300, y + 70), radius=12, outline="black", width=3, fill="#DDEBF7")
        d.text((x + 12, y + 22), name, fill="black", font=f)
    lanes = [((210, 190), (500, 270), "Lane L1: 1 day, PCM shipper 96h"),
             ((720, 300), (800, 160), "Lane L2: 2 days, PCM shipper 120h"),
             ((720, 320), (800, 460), "Lane L3: 1 day, active container")]
    for (x1, y1), (x2, y2), label in lanes:
        d.line((x1, y1, x2, y2), fill="black", width=3)
        d.text((min(x1, x2) - 10, (y1 + y2) / 2 + (15 if y2 > y1 else -40)), label, fill="#1F4E79", font=f)
    d.text((40, 560), "All lanes: data logger every 10 minutes; summer lanes Jun-Sep use +20% coolant mass.", fill="black", font=f)
    return _png(img)


def temperature_chart_png() -> bytes:
    """Temperature log chart for the deviation (peak value only appears in the chart)."""
    img = Image.new("RGB", (1000, 520), "white")
    d = ImageDraw.Draw(img)
    f, fb = font(20), font(24)
    d.text((30, 15), "Figure 3 - Shipment SHP-88213 data logger, lot LOT-24117", fill="black", font=fb)
    x0, y0, w, h = 90, 70, 860, 360
    d.rectangle((x0, y0, x0 + w, y0 + h), outline="black", width=2)
    def ty(t): return y0 + h - (t - 0) / 16 * h
    for t in (2, 8):
        d.line((x0, ty(t), x0 + w, ty(t)), fill="#C00000", width=2)
        d.text((x0 - 60, ty(t) - 12), f"{t} C", fill="#C00000", font=f)
    temps = [5.1, 5.3, 5.0, 5.6, 6.2, 7.4, 9.1, 11.3, 12.6, 11.8, 10.2, 8.9, 7.6, 6.1, 5.4, 5.2]
    pts = [(x0 + i * w / (len(temps) - 1), ty(t)) for i, t in enumerate(temps)]
    d.line(pts, fill="#1F4E79", width=4)
    d.text((x0 + 8 * w / 15 - 60, ty(12.6) - 40), "peak 12.6 C at 14:40", fill="#1F4E79", font=f)
    d.text((x0, y0 + h + 15), "Time on tarmac (Memphis): 11:00 - 17:00; cumulative time above 8 C: 3 h 20 min", fill="black", font=f)
    return _png(img)


def _png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------- PDF (SOP)
def write_sop_pdf(path: Path) -> None:
    doc = pymupdf.open()
    doc.set_metadata({"title": "Cold Chain Shipping Procedure"})
    page = doc.new_page()
    y = 60

    def text(s, size=11, bold=False, gap=6):
        nonlocal y, page
        if y > 760:
            page = doc.new_page()
            y = 60
        rect = pymupdf.Rect(56, y, 540, y + 400)
        used = page.insert_textbox(rect, s, fontsize=size, fontname="hebo" if bold else "helv")
        y += (400 - used) + gap if used > 0 else size * 2

    def table(rows, widths):
        nonlocal y
        x = 56
        for r, row in enumerate(rows):
            cx = x
            for c, cell in enumerate(row):
                rect = pymupdf.Rect(cx, y, cx + widths[c], y + 22)
                page.draw_rect(rect, color=(0, 0, 0), width=0.7)
                page.insert_textbox(rect + (4, 4, -2, 0), cell, fontsize=9, fontname="hebo" if r == 0 else "helv")
                cx += widths[c]
            y += 22
        y += 12

    text("Cold Chain Shipping Procedure", 18, True)
    text("Document ID: SOP-CC-001 | Revision: 6 | Owner: Distribution Quality | Classification: Internal", 9)
    text("Purpose", 14, True)
    text("This procedure defines how temperature-sensitive biologics (labelled storage 2-8 C) are packed, shipped, "
         "monitored and released. It applies to all lanes from the manufacturing site to distribution centres and hubs.")
    text("Packaging Configurations", 14, True)
    text("Select the packaging configuration from the table below. Summer configuration applies June to September.")
    table([["Configuration", "Qualified duration", "Coolant", "Use for"],
           ["PCM shipper 96h", "96 hours", "4 PCM panels (5 C)", "Lane L1, winter L2"],
           ["PCM shipper 120h", "120 hours", "6 PCM panels (5 C)", "Lane L2"],
           ["Active container", "unlimited (powered)", "compressor unit", "Lane L3, > 200 vials"]], [120, 110, 120, 134])
    text("Monitoring", 14, True)
    text("Every shipper carries a calibrated data logger recording every 10 minutes. Loggers are downloaded at "
         "receipt and the file is attached to the shipment record before release.")
    page.insert_image(pymupdf.Rect(56, y, 540, y + 330), stream=flowchart_png())
    y += 345
    text("Excursion Handling", 14, True)
    text("When a logger alarms, follow the decision flow in Figure 1. QA decides on release, quarantine or rejection; "
         "warehouse staff must not release a lot with an open excursion.")
    page = doc.new_page()
    y = 60
    text("Distribution Network", 14, True)
    text("The network and lane-specific packaging are shown in Figure 2.")
    page.insert_image(pymupdf.Rect(56, y, 540, y + 275), stream=network_png())
    y += 290
    text("Records", 14, True)
    text("Shipment records, logger files and excursion assessments are retained for 7 years.")
    doc.save(path, garbage=4, deflate=True, deflate_images=True)


# ---------------------------------------------------------------- Word (deviation)
def write_deviation_docx(path: Path) -> None:
    d = docx.Document()
    d.core_properties.title = "Deviation Report - Temperature Excursion"
    d.add_heading("Deviation Report - Temperature Excursion", level=1)
    for line in ("Document ID: DEV-2026-014", "Revision: 1", "Owner: Quality Assurance", "Classification: Confidential"):
        d.add_paragraph(line)
    d.add_heading("Summary", level=2)
    d.add_paragraph("During shipment SHP-88213 of lot LOT-24117 (Neuravex 100 mg vials) from the Manufacturing Site to the "
                    "Central DC on 14 August 2026, the shipper was left on the tarmac in Memphis during a flight delay. "
                    "The data logger recorded an excursion above 8 C.")
    d.add_heading("Timeline", level=2)
    t = d.add_table(rows=1, cols=2)
    t.style = "Table Grid"
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = "Time", "Event"
    for a, b in [("09:30", "Shipper tendered to carrier (PCM shipper 96h)"), ("11:00", "Flight delay; shipper held on tarmac"),
                 ("12:40", "Logger exceeds 8 C"), ("17:00", "Shipper moved to cold room"), ("18:15", "QA notified; lot placed on HOLD")]:
        row = t.add_row().cells
        row[0].text, row[1].text = a, b
    d.add_heading("Temperature Data", level=2)
    d.add_paragraph("The logger trace is shown in Figure 3.")
    d.add_picture(io.BytesIO(temperature_chart_png()), width=Inches(6))
    d.add_heading("Root Cause", level=2)
    d.add_paragraph("The carrier did not follow the hand-off requirement to move temperature-controlled freight to a cold "
                    "room within 60 minutes of a delay. The 96h PCM configuration was adequate for transit time but not "
                    "for 6 hours of direct summer sun.")
    d.add_heading("Disposition and CAPA", level=2)
    d.add_paragraph("Cumulative time above 8 C exceeded 2 hours, so the lot was quarantined per SOP-CC-001. No reading "
                    "exceeded 25 C and the lot was not frozen, so QA performed a stability review. Based on stability data "
                    "the lot was released on 22 August 2026. CAPA-2026-031: carrier re-training and a summer tarmac "
                    "exclusion clause; summer lanes now use +20% coolant mass.")
    d.save(path)


# ---------------------------------------------------------------- HTML, Markdown, CSV
SUPPLIERS = [("SUP-101", "Polar Pack Solutions", "Insulated shippers", "Approved", 94, "2026-03-12"),
             ("SUP-104", "ThermoTrack Loggers", "Data loggers", "Approved", 91, "2026-01-20"),
             ("SUP-112", "SkyCold Logistics", "Air freight carrier", "Conditional", 72, "2026-08-28"),
             ("SUP-118", "VialGlass Corp", "Primary containers", "Approved", 88, "2025-11-05"),
             ("SUP-121", "FrostLine Couriers", "Ground carrier", "Disqualified", 55, "2026-06-30")]


def write_supplier_html(path: Path) -> None:
    rows = "\n".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td><td>{d}</td><td>{e}</td><td>{f}</td></tr>"
                     for a, b, c, d, e, f in SUPPLIERS)
    path.write_text(f"""<!doctype html><html><head><title>Supplier Qualification Status 2026</title></head><body>
<h1>Supplier Qualification Status 2026</h1>
<p>Document ID: SUP-QUAL-2026 | Owner: Supplier Quality | Classification: Internal</p>
<h2>Qualification Criteria</h2>
<ul><li>Approved: audit score 85 or higher and no open critical findings.</li>
<li>Conditional: score 70-84; shipments allowed with enhanced monitoring and a CAPA due within 90 days.</li>
<li>Disqualified: score below 70 or a critical GDP finding; no new orders.</li></ul>
<h2>Supplier Scorecard</h2>
<table><tr><th>Supplier ID</th><th>Supplier</th><th>Category</th><th>Status</th><th>Audit score</th><th>Last audit</th></tr>
{rows}</table>
<h2>Notes</h2>
<p>SkyCold Logistics moved to Conditional after deviation DEV-2026-014 (tarmac exposure). FrostLine Couriers was
disqualified after repeated temperature excursions on ground routes.</p>
</body></html>""", encoding="utf-8")


POLICY = """# Good Distribution Practice Policy

Document ID: GDP-POL-001 | Owner: Head of Quality | Classification: Public

## Scope
This policy applies to the storage and distribution of all medicinal products by the company and its partners.

## Principles
- Products are stored and transported within their labelled conditions at all times.
- Every shipment of temperature-sensitive product is monitored with a calibrated data logger.
- Partners must report any deviation within 24 hours.
- Only qualified suppliers and carriers may handle product.

## Partner Responsibilities
- Follow the shipper conditioning instructions supplied with each shipment.
- Move temperature-controlled freight to a controlled environment within 60 minutes of any delay.
- Keep records for at least 7 years and make them available for audit.
"""


def write_inventory(path: Path) -> None:
    products = ["Neuravex 100 mg vial", "Cognira 50 mg vial", "Myelix 20 mg prefilled syringe"]
    sites = ["Manufacturing Site (Durham, NC)", "Central DC (Memphis, TN)", "West Hub (Reno, NV)", "East Hub (Allentown, PA)"]
    rows = []
    for i in range(30):
        lot = f"LOT-{24100 + i}"
        status = "released"
        exc = 0
        if lot == "LOT-24117":
            status, exc = "released", 1
        elif i in (5, 22):
            status, exc = "quarantine", 1
        rows.append({"lot_id": lot, "product": products[i % 3], "site": sites[i % 4], "quantity_vials": random.randint(200, 4800),
                     "expiry": f"2027-{(i % 12) + 1:02d}-28", "storage": "2-8 C", "status": status, "excursions": exc})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    write_sop_pdf(RAW / "SOP-CC-001_cold_chain_shipping.pdf")
    write_deviation_docx(RAW / "DEV-2026-014_temperature_excursion.docx")
    write_supplier_html(RAW / "SUP-QUAL-2026_supplier_qualification.html")
    (RAW / "GDP-POL-001_good_distribution_practice.md").write_text(POLICY, encoding="utf-8")
    write_inventory(RAW / "inventory_lots.csv")
    print(f"Wrote PDF, Word, HTML, Markdown and CSV sources to {RAW}")


if __name__ == "__main__":
    main()
