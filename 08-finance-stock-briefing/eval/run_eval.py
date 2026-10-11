"""Offline evaluation (no LLM needed unless --briefings is given).

    python -m eval.run_eval                  # filing extraction, retrieval, guardrails, computed metrics, compliance filter
    python -m eval.run_eval --briefings 2    # + end-to-end LLM briefings: section coverage, citations, compliance, latency

Results -> eval/results/eval_report.json
"""

import argparse
import json
import statistics
from pathlib import Path

from stockbrief.config import get_settings
from stockbrief.financials import metrics, synthetic_financials
from stockbrief.guardrails import check_input, compliance_review
from stockbrief.ingest import ensure_index, synthetic_filings
from stockbrief.market import price_metrics, synthetic_quote
from stockbrief.retrieval import get_retrievers

HERE = Path(__file__).parent
OUT = HERE / "results"


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (HERE / "datasets" / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def eval_extraction() -> dict:
    expected = {"10-K": ["1", "1A", "7"], "10-Q": ["I-2", "II-1A"], "8-K": ["8-K"]}
    checks = {}
    for f in synthetic_filings():
        md = "\n".join(m for _, m in f.sections.values())
        checks[f.doc_id] = {"sections_found": sorted(f.sections) == sorted(expected[f.form]),
                            "page_furniture_removed": "Table of Contents" not in md and "\n\n6\n\n" not in md,
                            "no_hidden_xbrl": "XBRL hidden facts" not in md}
    passed = sum(all(v.values()) for v in checks.values())
    return {"filings_passed": passed, "filings": len(checks), "checks": checks}


def eval_retrieval(k: int) -> dict:
    store = get_retrievers()["filings"]
    per = []
    for row in load("rag_dataset.jsonl"):
        hits = store.search(row["question"], k, {"ticker": row["ticker"]})
        ranks = [i for i, h in enumerate(hits, start=1)
                 if h["metadata"]["doc_id"] in row["reference_docs"] and any(m in h["content"] for m in row["must_contain"])]
        per.append({"question": row["question"], "hit": bool(ranks), "rr": 1 / ranks[0] if ranks else 0.0,
                    "cross_ticker_chunks": sum(h["metadata"]["ticker"] != row["ticker"] for h in hits)})
    return {"k": k, "hit_rate": round(statistics.mean(p["hit"] for p in per), 3), "mrr": round(statistics.mean(p["rr"] for p in per), 3),
            "cross_ticker_chunks": sum(p["cross_ticker_chunks"] for p in per), "misses": [p for p in per if not p["hit"]]}


def eval_guardrails() -> dict:
    tp = fp = fn = 0
    wrong = []
    for row in load("guardrail_dataset.jsonl"):
        cat = check_input(row["text"]).category
        tp += cat is not None and row["expected"] is not None
        fp += cat is not None and row["expected"] is None
        fn += cat is None and row["expected"] is not None
        if cat != row["expected"]:
            wrong.append({"text": row["text"], "expected": row["expected"], "got": cat})
    return {"precision": round(tp / (tp + fp), 3) if tp + fp else 1.0, "recall": round(tp / (tp + fn), 3) if tp + fn else 1.0, "wrong": wrong}


def eval_metrics() -> dict:
    """Computed figures vs hand-calculated values from the source data."""
    n, h = metrics(synthetic_financials("NWRB")), metrics(synthetic_financials("HLXB"))
    pm = price_metrics(synthetic_quote("NWRB"), n["eps_diluted"], None)
    checks = {"nwrb_revenue_growth": n["revenue_growth_pct"] == round((1541.3 / 1356.9 - 1) * 100, 1),
              "nwrb_gross_margin": n["gross_margin_pct"] == round(693.6 / 1541.3 * 100, 1),
              "nwrb_pe": pm["pe_fy"] == round(64.82 / 2.31, 1),
              "hlxb_pe_not_meaningful": price_metrics(synthetic_quote("HLXB"), h["eps_diluted"], None)["pe_fy"] is None,
              "hlxb_quarter_growth": h["quarter_revenue_growth_pct"] == round((52.3 / 46.1 - 1) * 100, 1)}
    return {"passed": sum(checks.values()), "total": len(checks), "checks": checks}


def eval_compliance_filter() -> dict:
    advice = ["We recommend buying NWRB ahead of the outlook raise.", "HLXB looks undervalued after the selloff.",
              "Our price target implies 20% upside.", "Investors should buy before the BLA.", "This is a strong buy recommendation."]
    factual = ["Revenue grew 13.6% to $1,541.3 million.", "The company raised its outlook to 13% to 15%.",
               "Cash is expected to fund operations into 2028.", "Analysts will watch the BLA submission in 2027."]
    out = compliance_review({"x": advice + factual}, "13.6% $1,541.3 million 13% to 15% 2028 2027 20%")
    return {"advice_removed": len(out.removed), "advice_total": len(advice), "factual_kept": len(out.sections["x"]), "factual_total": len(factual)}


def eval_briefings(n: int) -> list[dict]:
    from stockbrief.service import get_service

    results = []
    for company, role in [("NWRB", "financial_advisor"), ("HLXB", "research_analyst")][:n]:
        r = get_service().brief(company, role, "synthetic", "eval")
        b = r["briefing"] or {}
        sections = b.get("sections", {})
        bullets = [x for v in sections.values() for x in v]
        results.append({"company": company, "role": role, "outcome": r["outcome"], "latency_s": round(r["latency_ms"] / 1000, 1),
                        "llm_written": b.get("llm_written"), "sections_filled": sum(bool(v) for v in sections.values()), "sections_expected": len(sections),
                        "bullets_with_citation": round(statistics.mean(["[" in x for x in bullets] or [0]), 3),
                        "statements_removed_by_compliance": len(b.get("removed_statements", [])), "output_issues": r["guardrail"].get("output_issues")})
        print(results[-1], flush=True)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefings", type=int, default=0)
    args = ap.parse_args()
    ensure_index()
    report = {"extraction": eval_extraction(), "retrieval": eval_retrieval(get_settings().top_k), "guardrails": eval_guardrails(),
              "computed_metrics": eval_metrics(), "compliance_filter": eval_compliance_filter()}
    if args.briefings:
        report["briefings"] = eval_briefings(args.briefings)
    OUT.mkdir(exist_ok=True)
    (OUT / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for name, section in report.items():
        print(f"\n== {name}\n{json.dumps(section, indent=1)[:1200]}")


if __name__ == "__main__":
    main()
