"""Generates the synthetic market and filings data for the Stock Briefing Assistant.

    python data/generate_data.py

Two FICTIONAL companies (tickers checked against the SEC ticker list - not in use):
  NWRB  Northwind Robotics Inc.   industrial automation, profitable, tariff and customer-concentration risks
  HLXB  Helix Biologics Corp.     clinical-stage biotech, loss-making; its pipeline (HLX-INS7, HLX-SERCA, ...) is the
                                  same one that appears in project 07's synthetic trial registry

Outputs (committed) in data/raw/:
  companies.json          profile: name, exchange, sector, CIK-like ID, fiscal year end
  quotes.json             quote snapshot + 52 weekly closes per ticker
  financials.json         XBRL-companyfacts-like annual (FY2023-FY2025) and latest-quarter facts
  filings/<TICKER>/       EDGAR-style HTML: 10-K (with a table of contents, running "Table of Contents" links and
                          page numbers - the noise a real filing has), 10-Q, 8-K, plus filings_index.json

All companies, people, customers, figures and events are fictional. Not investment research.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path

RAW = Path(__file__).parent / "raw"

COMPANIES = {
    "NWRB": {"name": "Northwind Robotics Inc.", "exchange": "NASDAQ", "sector": "Industrials", "industry": "Industrial automation and robotics",
             "cik": "0009900101", "fiscal_year_end": "12-31", "hq": "Columbus, Ohio", "employees": 4120},
    "HLXB": {"name": "Helix Biologics Corp.", "exchange": "NASDAQ", "sector": "Health Care", "industry": "Biotechnology",
             "cik": "0009900202", "fiscal_year_end": "12-31", "hq": "Cambridge, Massachusetts", "employees": 860},
}

FINANCIALS = {   # USD millions except EPS (USD per diluted share)
    "NWRB": {
        "annual": [
            {"fy": 2023, "revenue": 1184.2, "gross_profit": 509.2, "operating_income": 97.1, "net_income": 71.0, "eps_diluted": 1.32,
             "rd_expense": 142.6, "cash": 301.4, "total_debt": 420.0, "diluted_shares": 53.8},
            {"fy": 2024, "revenue": 1356.9, "gross_profit": 597.0, "operating_income": 130.3, "net_income": 98.7, "eps_diluted": 1.83,
             "rd_expense": 163.0, "cash": 355.2, "total_debt": 385.0, "diluted_shares": 53.9},
            {"fy": 2025, "revenue": 1541.3, "gross_profit": 693.6, "operating_income": 161.8, "net_income": 124.5, "eps_diluted": 2.31,
             "rd_expense": 184.9, "cash": 412.6, "total_debt": 350.0, "diluted_shares": 53.9},
        ],
        "quarter": {"period": "Q2 2026", "end": "2026-06-30", "revenue": 418.7, "net_income": 36.9, "eps_diluted": 0.68,
                    "prior_year": {"period": "Q2 2025", "revenue": 371.2, "net_income": 29.8, "eps_diluted": 0.55}},
    },
    "HLXB": {
        "annual": [
            {"fy": 2023, "revenue": 142.5, "gross_profit": 142.5, "operating_income": -265.8, "net_income": -251.2, "eps_diluted": -2.98,
             "rd_expense": 331.4, "cash": 1402.7, "total_debt": 0.0, "diluted_shares": 84.3},
            {"fy": 2024, "revenue": 168.0, "gross_profit": 168.0, "operating_income": -289.5, "net_income": -270.9, "eps_diluted": -3.15,
             "rd_expense": 372.8, "cash": 1268.4, "total_debt": 0.0, "diluted_shares": 86.0},
            {"fy": 2025, "revenue": 191.4, "gross_profit": 191.4, "operating_income": -321.7, "net_income": -298.6, "eps_diluted": -3.41,
             "rd_expense": 412.7, "cash": 1105.3, "total_debt": 0.0, "diluted_shares": 87.6},
        ],
        "quarter": {"period": "Q2 2026", "end": "2026-06-30", "revenue": 52.3, "net_income": -81.2, "eps_diluted": -0.91,
                    "prior_year": {"period": "Q2 2025", "revenue": 46.1, "net_income": -72.5, "eps_diluted": -0.83}},
    },
}

QUOTE = {"NWRB": {"price": 64.82, "previous_close": 63.95, "day_low": 63.70, "day_high": 65.21, "volume": 1_420_000, "avg_volume": 1_650_000,
                  "shares_outstanding_m": 53.1, "start": 46.0},
         "HLXB": {"price": 38.15, "previous_close": 40.02, "day_low": 37.80, "day_high": 40.10, "volume": 3_900_000, "avg_volume": 2_300_000,
                  "shares_outstanding_m": 89.4, "start": 29.5}}
AS_OF = "2026-10-09T16:00:00-04:00"


def weekly_closes(ticker: str, q: dict) -> list[dict]:
    rnd = random.Random(ticker)
    n, start, end = 52, q["start"], q["price"]
    closes, price = [], start
    for i in range(n):
        drift = (end - price) / (n - i)
        price = max(1.0, price + drift + rnd.gauss(0, start * 0.035))
        closes.append(round(price, 2))
    closes[-1] = end
    d0 = date(2026, 10, 9) - timedelta(weeks=n - 1)
    return [{"date": (d0 + timedelta(weeks=i)).isoformat(), "close": c} for i, c in enumerate(closes)]


# ---------------------------------------------------------------- EDGAR-style HTML
def _html(title: str, body: str) -> str:
    return f"""<html><head><title>{title}</title></head><body>
<div style="display:none"><ix:header>XBRL hidden facts would be here</ix:header></div>
{body}
</body></html>
"""


def _toc_link(page: int) -> str:
    # running page furniture found in real filings: a back-link and a page number on every "page"
    return f'<p style="text-align:center"><a href="#toc">Table of Contents</a></p><p style="text-align:center">{page}</p><hr/>'


def _table(rows: list[list[str]]) -> str:
    out = ["<table>"]
    for i, r in enumerate(rows):
        tag = "th" if i == 0 else "td"
        # real filings split "$" and the number into separate cells and add empty spacer cells
        cells = "".join(f"<{tag}>{c}</{tag}><td></td>" if i and j else f"<{tag}>{c}</{tag}>" for j, c in enumerate(r))
        out.append(f"<tr>{cells}</tr>")
    return "".join(out) + "</table>"


def _heading(item: str, title: str) -> str:
    # styled spans split words, as in real inline-XBRL filings ("RIS K FACTORS")
    head, tail = title[: len(title) // 2], title[len(title) // 2:]
    return f'<p style="font-weight:bold"><span>ITEM {item}. </span><span>{head}</span><span>{tail}</span></p>'


def ten_k(t: str) -> str:
    c, f = COMPANIES[t], FINANCIALS[t]
    a = {r["fy"]: r for r in f["annual"]}
    toc = _table([["Item", "Description", "Page"], ["Item 1.", "Business", "3"], ["Item 1A.", "Risk Factors", "7"],
                  ["Item 1C.", "Cybersecurity", "15"], ["Item 2.", "Properties", "16"], ["Item 7.", "Management's Discussion and Analysis", "18"],
                  ["Item 8.", "Financial Statements and Supplementary Data", "30"]])
    if t == "NWRB":
        business = [
            ("Northwind Robotics designs, manufactures and services collaborative robots (cobots), autonomous mobile robots (AMRs) and the "
            "FleetOS software that orchestrates them in factories and warehouses. We sell to automotive, electronics, logistics and "
            "food-and-beverage manufacturers in 31 countries."),
            ("We report two segments: Robotics Systems (cobots and AMRs, 78% of 2025 revenue) and Software and Services (FleetOS "
            "subscriptions, maintenance and integration, 22% of 2025 revenue). FleetOS annual recurring revenue (ARR) reached $212 million "
            "at December 31, 2025."),
            ("Our three largest customers, all automotive manufacturers, accounted for 31% of 2025 revenue. Revenue outside the United States "
            "was 38% of the total. We employ 4,120 people and manufacture in Columbus, Ohio and Monterrey, Mexico.")]
        risks = [
            ("Customer concentration.", ("Our three largest customers accounted for 31% of revenue in 2025. A delay or cancellation of an "
             "automotive retooling program could reduce revenue materially.")),
            ("Tariffs and trade policy.", ("Harmonic-drive actuators and controllers are imported from suppliers in Asia. New or higher tariffs "
             "would increase cost of revenue; we estimate each 10 percentage points of tariff on these components reduces gross margin by "
             "about 60 basis points.")),
            ("Competition.", ("Low-cost cobot manufacturers continue to enter the market, and large industrial-automation companies bundle "
             "robots with their control systems, which may pressure our pricing.")),
            ("Semiconductor supply.", "We rely on a single source for the safety-rated motion controller used in all cobot models."),
            ("Cybersecurity of connected fleets.", ("FleetOS connects customer robots to our cloud. A security incident could disrupt "
             "customer operations and expose us to liability.")),
            ("Foreign currency.", ("38% of revenue is denominated in currencies other than the U.S. dollar, mainly the euro and the "
             "Mexican peso."))]
        mdna = [
            ("Revenue grew 13.6% to $1,541.3 million in 2025, driven by AMR shipments (+24%) and FleetOS subscriptions (+31%). Robotics "
            "Systems revenue grew 9.8% as automotive retooling slowed in the second half."),
            ("Gross margin expanded 100 basis points to 45.0% on a higher software mix and lower freight costs. Operating income rose to "
            "$161.8 million (10.5% operating margin) from $130.3 million."),
            "Research and development expense increased to $184.9 million (12.0% of revenue), reflecting the next-generation AMR platform.",
            ("Liquidity: cash and cash equivalents were $412.6 million and total debt was $350.0 million at year end. We repaid $35.0 "
            "million of term debt in 2025."),
            "Outlook: for 2026 we expect revenue growth of 11% to 13% and a modest improvement in operating margin."]
    else:
        business = [
            ("Helix Biologics is a clinical-stage biotechnology company developing biologic and genetic medicines for cardiometabolic "
            "disease. Our revenue consists of royalties and collaboration revenue from partnered programs; we have no product approved for sale."),
            ("Our lead program is HLX-INS7, a once-weekly basal insulin in Phase 3 (study SYN-DM-203) for type 2 diabetes. Other programs "
            "include HLX-SERCA, an AAV gene therapy for heart failure with reduced ejection fraction (Phase 2, SYN-HF-103), HLX-207, an "
            "anti-fibrotic antibody (Phase 1, SYN-HF-109), and HLX-AMY, an amylin co-agonist (Phase 1, SYN-DM-210)."),
            "We employ 860 people and operate a clinical-scale AAV manufacturing facility in Cambridge, Massachusetts."]
        risks = [
            ("Clinical development risk.", "HLX-INS7 may fail to meet its endpoints or regulators may require additional studies before approval."),
            ("Dependence on HLX-INS7.", "A substantial part of our valuation depends on HLX-INS7; a setback would materially affect our prospects."),
            ("Gene therapy manufacturing.", "AAV vector manufacturing is complex and capacity-constrained; batch failures could delay HLX-SERCA."),
            ("Competition.", "Large insulin manufacturers market daily and weekly basal insulins with established payer contracts."),
            ("Need for additional capital.", ("We had $1,105.3 million of cash and investments at year end and expect it to fund operations "
             "into 2028. We may raise additional equity, which would dilute shareholders.")),
            ("Pricing and reimbursement.", "Government price negotiation and payer formulary decisions could limit the price of future products.")]
        mdna = [
            ("Revenue increased 13.9% to $191.4 million in 2025, reflecting higher royalties on a partnered product and a $12.0 million "
            "collaboration milestone."),
            ("Research and development expense increased to $412.7 million from $372.8 million, driven by Phase 3 enrollment for HLX-INS7 "
            "and AAV manufacturing scale-up for HLX-SERCA."),
            "Net loss was $298.6 million, or $3.41 per diluted share, compared with $270.9 million, or $3.15 per diluted share, in 2024.",
            "Liquidity: cash, cash equivalents and marketable securities were $1,105.3 million at December 31, 2025. We have no debt.",
            "Outlook: we expect topline Phase 3 results for HLX-INS7 in the second half of 2026 and a biologics license application in 2027 if positive."]
    fin_rows = [["(in millions, except per share)", "2025", "2024", "2023"],
                ["Revenue", f"{a[2025]['revenue']:,.1f}", f"{a[2024]['revenue']:,.1f}", f"{a[2023]['revenue']:,.1f}"],
                ["Research and development", f"{a[2025]['rd_expense']:,.1f}", f"{a[2024]['rd_expense']:,.1f}", f"{a[2023]['rd_expense']:,.1f}"],
                ["Operating income (loss)", f"{a[2025]['operating_income']:,.1f}", f"{a[2024]['operating_income']:,.1f}", f"{a[2023]['operating_income']:,.1f}"],
                ["Net income (loss)", f"{a[2025]['net_income']:,.1f}", f"{a[2024]['net_income']:,.1f}", f"{a[2023]['net_income']:,.1f}"],
                ["Diluted EPS", f"{a[2025]['eps_diluted']:.2f}", f"{a[2024]['eps_diluted']:.2f}", f"{a[2023]['eps_diluted']:.2f}"]]
    body = [(f"<p>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</p><p>FORM 10-K</p><p>Annual report for the fiscal year ended "
            f"December 31, 2025</p><p>{c['name']} (Nasdaq: {t})</p><p>SYNTHETIC FILING - FICTIONAL COMPANY</p>"),
            '<p id="toc">TABLE OF CONTENTS</p>', toc, _toc_link(2), "<p>PART I</p>", _heading("1", "BUSINESS")]
    body += [f"<p>{p}</p>" for p in business] + [_toc_link(6), _heading("1A", "RISK FACTORS"),
             "<p>Investing in our common stock involves risks. The risks below could materially affect our business.</p>"]
    for title, text in risks:
        body.append(f"<p><b><i>{title}</i></b> {text}</p>")
    body += [_toc_link(14), _heading("1C", "CYBERSECURITY"),
             "<p>Our chief information security officer reports quarterly to the audit committee on cybersecurity risk.</p>",
             _heading("2", "PROPERTIES"), f"<p>Our headquarters are in {c['hq']}.</p>", _toc_link(17), "<p>PART II</p>",
             _heading("7", "MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS")]
    body += [f"<p>{p}</p>" for p in mdna] + [_table(fin_rows), _toc_link(29), _heading("8", "FINANCIAL STATEMENTS AND SUPPLEMENTARY DATA"),
             "<p>The consolidated financial statements are included in the XBRL financial data accompanying this report.</p>"]
    return _html(f"{c['name']} 10-K 2025", "\n".join(body))


def ten_q(t: str) -> str:
    c, q = COMPANIES[t], FINANCIALS[t]["quarter"]
    p = q["prior_year"]
    if t == "NWRB":
        mdna = [(f"Revenue for the quarter ended June 30, 2026 was ${q['revenue']} million, up 12.8% from ${p['revenue']} million, led by AMRs "
                "and FleetOS subscriptions. Backlog was $1.02 billion at quarter end."),
                (f"Net income was ${q['net_income']} million (${q['eps_diluted']} per diluted share) compared with ${p['net_income']} million "
                f"(${p['eps_diluted']}) a year earlier. Gross margin was 45.4%.")]
        risk_update = ("In May 2026 a new 15% tariff took effect on certain imported actuators. We expect it to reduce 2026 gross margin by "
                       "about 90 basis points before mitigation through dual sourcing in Mexico.")
    else:
        mdna = [f"Revenue for the quarter ended June 30, 2026 was ${q['revenue']} million compared with ${p['revenue']} million.",
                (f"Net loss was ${abs(q['net_income'])} million (${abs(q['eps_diluted'])} per diluted share) compared with "
                f"${abs(p['net_income'])} million a year earlier, reflecting Phase 3 close-out costs for HLX-INS7."),
                "Cash, cash equivalents and marketable securities were $968.4 million at June 30, 2026."]
        risk_update = ("The FDA requested additional long-term liver-safety follow-up for HLX-SERCA participants, which may extend the "
                       "Phase 2 timeline by about six months.")
    body = [(f"<p>FORM 10-Q</p><p>Quarterly report for the period ended June 30, 2026</p><p>{c['name']} (Nasdaq: {t})</p>"
            "<p>SYNTHETIC FILING - FICTIONAL COMPANY</p>"), '<p id="toc">TABLE OF CONTENTS</p>',
            _table([["Item", "Description"], ["Part I, Item 2.", "MD&A"], ["Part II, Item 1A.", "Risk Factors"]]),
            "<p>PART I - FINANCIAL INFORMATION</p>", _heading("1", "FINANCIAL STATEMENTS"),
            "<p>Condensed consolidated financial statements are provided in the XBRL data.</p>",
            _heading("2", "MANAGEMENT'S DISCUSSION AND ANALYSIS OF FINANCIAL CONDITION AND RESULTS OF OPERATIONS")]
    body += [f"<p>{x}</p>" for x in mdna] + [_toc_link(12), "<p>PART II - OTHER INFORMATION</p>", _heading("1", "LEGAL PROCEEDINGS"),
             "<p>None.</p>", _heading("1A", "RISK FACTORS"), f"<p>{risk_update}</p>"]
    return _html(f"{c['name']} 10-Q Q2 2026", "\n".join(body))


def eight_k(t: str) -> tuple[str, str, str]:
    c = COMPANIES[t]
    if t == "NWRB":
        filed, items = "2026-09-15", "1.01, 7.01"
        text = [("Item 1.01 Entry into a Material Definitive Agreement", ("On September 12, 2026, Northwind Robotics entered into a five-year "
                 "supply agreement with Atlas Motor Group, a fictional automotive manufacturer, for AMRs and FleetOS subscriptions with an "
                 "expected value of approximately $240 million.")),
                ("Item 7.01 Regulation FD Disclosure", "The company raised its 2026 revenue growth outlook to 13% to 15%, from 11% to 13%.")]
    else:
        filed, items = "2026-10-01", "8.01"
        text = [("Item 8.01 Other Events", ("Helix Biologics announced topline results from the Phase 3 study SYN-DM-203 of HLX-INS7, a "
                 "once-weekly basal insulin, in 1,500 adults with type 2 diabetes. HLX-INS7 met the primary endpoint of non-inferior A1C "
                 "reduction at 52 weeks (-1.42 percentage points versus -1.31 for once-daily basal insulin). Rates of clinically significant "
                 "hypoglycemia were similar between groups. The company plans a biologics license application in the first quarter of 2027."))]
    body = [(f"<p>FORM 8-K</p><p>Current report - date of report {filed}</p><p>{c['name']} (Nasdaq: {t})</p>"
            "<p>SYNTHETIC FILING - FICTIONAL COMPANY</p>")]
    for head, para in text:
        body += [f"<p><b>{head}</b></p>", f"<p>{para}</p>"]
    return _html(f"{c['name']} 8-K {filed}", "\n".join(body)), filed, items


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "companies.json").write_text(json.dumps(COMPANIES, indent=2), encoding="utf-8")
    (RAW / "financials.json").write_text(json.dumps(FINANCIALS, indent=2), encoding="utf-8")
    quotes = {}
    for t, q in QUOTE.items():
        series = weekly_closes(t, q)
        closes = [s["close"] for s in series]
        quotes[t] = {"symbol": t, "name": COMPANIES[t]["name"], "currency": "USD", "exchange": COMPANIES[t]["exchange"], "as_of": AS_OF,
                     "price": q["price"], "previous_close": q["previous_close"], "day_low": q["day_low"], "day_high": q["day_high"],
                     "fifty_two_week_low": min(closes + [q["day_low"]]), "fifty_two_week_high": max(closes + [q["day_high"]]),
                     "volume": q["volume"], "avg_volume": q["avg_volume"], "shares_outstanding_m": q["shares_outstanding_m"],
                     "weekly_closes": series, "source": "synthetic"}
    (RAW / "quotes.json").write_text(json.dumps(quotes, indent=2), encoding="utf-8")
    for t in COMPANIES:
        d = RAW / "filings" / t
        d.mkdir(parents=True, exist_ok=True)
        index = []
        (d / "10-K_2026-02-24.html").write_text(ten_k(t), encoding="utf-8")
        index.append({"form": "10-K", "filed": "2026-02-24", "period": "2025-12-31", "file": "10-K_2026-02-24.html",
                      "description": "Annual report for fiscal 2025"})
        (d / "10-Q_2026-08-04.html").write_text(ten_q(t), encoding="utf-8")
        index.append({"form": "10-Q", "filed": "2026-08-04", "period": "2026-06-30", "file": "10-Q_2026-08-04.html",
                      "description": "Quarterly report for Q2 2026"})
        html, filed, items = eight_k(t)
        (d / f"8-K_{filed}.html").write_text(html, encoding="utf-8")
        index.append({"form": "8-K", "filed": filed, "period": filed, "file": f"8-K_{filed}.html", "description": f"Current report, items {items}"})
        (d / "filings_index.json").write_text(json.dumps(sorted(index, key=lambda x: x["filed"], reverse=True), indent=2), encoding="utf-8")
    for p in sorted(RAW.rglob("*")):
        if p.is_file():
            print(f"{p.relative_to(RAW)!s:40s} {p.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
