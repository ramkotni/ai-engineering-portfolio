"""Key financials from structured data - never from LLM reading of the filing text.

  synthetic  data/raw/financials.json (XBRL-companyfacts-like, USD millions)
  live       SEC XBRL company facts: annual values = 10-K facts with a ~1-year duration, latest quarter = most recent
             10-Q fact with a ~3-month duration, compared with the same quarter a year earlier.
"""

import json
from datetime import date

from stockbrief.config import Settings, get_settings

CONCEPTS = {   # field -> (us-gaap concept candidates in priority order, unit)
    "revenue": (["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
                 "RevenueFromContractWithCustomerIncludingAssessedTax"], "USD"),
    "gross_profit": (["GrossProfit"], "USD"),
    "operating_income": (["OperatingIncomeLoss"], "USD"),
    "net_income": (["NetIncomeLoss"], "USD"),
    "eps_diluted": (["EarningsPerShareDiluted"], "USD/shares"),
    "rd_expense": (["ResearchAndDevelopmentExpense"], "USD"),
    "cash": (["CashAndCashEquivalentsAtCarryingValue"], "USD"),
    "total_debt": (["LongTermDebt", "LongTermDebtNoncurrent"], "USD"),
    "diluted_shares": (["WeightedAverageNumberOfDilutedSharesOutstanding"], "shares"),
}
INSTANT = {"cash", "total_debt"}


def synthetic_financials(ticker: str, settings: Settings | None = None) -> dict | None:
    s = settings or get_settings()
    return json.loads((s.data_dir / "financials.json").read_text(encoding="utf-8")).get(ticker.upper())


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def from_company_facts(facts: dict) -> dict:
    gaap = facts.get("facts", {}).get("us-gaap", {})
    annual: dict[str, dict] = {}
    quarters: dict[str, dict] = {}
    for field, (candidates, unit) in CONCEPTS.items():
        scale = 1 if unit == "USD/shares" else 1e6
        for concept in candidates:
            rows = gaap.get(concept, {}).get("units", {}).get(unit, [])
            if not rows:
                continue
            for r in rows:
                if field in INSTANT:
                    if r.get("form") == "10-K" and r.get("fp") == "FY":
                        annual.setdefault(r["end"], {})[field] = round(r["val"] / scale, 2)
                    continue
                length = _days(r["start"], r["end"]) if r.get("start") else 0
                if r.get("form") == "10-K" and 350 <= length <= 380:
                    annual.setdefault(r["end"], {}).setdefault(field, round(r["val"] / scale, 2))
                elif r.get("form") == "10-Q" and 80 <= length <= 100:
                    quarters.setdefault(r["end"], {}).setdefault(field, round(r["val"] / scale, 2))
            break                                          # first concept the company reports wins
    years = sorted(e for e in annual if "revenue" in annual[e])[-3:]
    out = {"annual": [{"fy": int(e[:4]), "period_end": e, **annual[e]} for e in years], "quarter": None}
    q_ends = sorted(e for e in quarters if "revenue" in quarters[e])
    if q_ends:
        latest = q_ends[-1]
        prior = next((e for e in q_ends if 355 <= _days(e, latest) <= 375), None)
        out["quarter"] = {"period": f"quarter ended {latest}", "end": latest, **quarters[latest],
                          "prior_year": {"period": f"quarter ended {prior}", **quarters[prior]} if prior else None}
    shares = facts.get("facts", {}).get("dei", {}).get("EntityCommonStockSharesOutstanding", {}).get("units", {}).get("shares", [])
    out["shares_outstanding_m"] = round(max(shares, key=lambda r: r["end"])["val"] / 1e6, 1) if shares else None
    return out


def _pct(a, b):
    return round((a / b - 1) * 100, 1) if a is not None and b not in (None, 0) and b > 0 else None


def metrics(fin: dict) -> dict:
    """Growth and margins computed in code (rounded) - these exact numbers are given to the LLM."""
    a = fin["annual"]
    last, prev = a[-1], a[-2] if len(a) > 1 else None
    rev = last.get("revenue")
    m = {
        "fiscal_year": last["fy"],
        "revenue_m": rev,
        "revenue_growth_pct": _pct(rev, prev.get("revenue")) if prev else None,
        "gross_margin_pct": round(last["gross_profit"] / rev * 100, 1) if last.get("gross_profit") is not None and rev else None,
        "operating_margin_pct": round(last["operating_income"] / rev * 100, 1) if last.get("operating_income") is not None and rev else None,
        "net_income_m": last.get("net_income"),
        "net_margin_pct": round(last["net_income"] / rev * 100, 1) if last.get("net_income") is not None and rev else None,
        "eps_diluted": last.get("eps_diluted"),
        "eps_growth_pct": _pct(last.get("eps_diluted"), prev.get("eps_diluted")) if prev else None,
        "rd_pct_of_revenue": round(last["rd_expense"] / rev * 100, 1) if last.get("rd_expense") and rev else None,
        "cash_m": last.get("cash"), "total_debt_m": last.get("total_debt"),
    }
    q = fin.get("quarter")
    if q and q.get("prior_year"):
        p = q["prior_year"]
        m |= {"quarter": q["period"], "quarter_revenue_m": q.get("revenue"), "quarter_revenue_growth_pct": _pct(q.get("revenue"), p.get("revenue")),
              "quarter_net_income_m": q.get("net_income"), "quarter_prior_net_income_m": p.get("net_income"),
              "quarter_eps_diluted": q.get("eps_diluted"), "quarter_prior_eps_diluted": p.get("eps_diluted")}
    return m


def get_financials(ticker: str, source: str, cik: str | None = None, settings: Settings | None = None) -> dict | None:
    if source == "live":
        from stockbrief.edgar import company_facts

        return from_company_facts(company_facts(cik, settings))
    return synthetic_financials(ticker, settings)
