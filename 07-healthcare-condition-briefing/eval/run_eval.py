"""Offline evaluation (no LLM needed unless --briefings is given).

    python -m eval.run_eval                  # extraction, retrieval, guardrails, registry analytics
    python -m eval.run_eval --briefings 2    # + end-to-end LLM briefings: section coverage, citations, grounding, latency

Results -> eval/results/eval_report.json
"""

import argparse
import csv
import json
import statistics
from collections import Counter
from pathlib import Path

from medbrief.conditions import CATALOGUE
from medbrief.config import get_settings
from medbrief.guardrails import check_input
from medbrief.ingest import ensure_index
from medbrief.retrieval import get_retrievers
from medbrief.trials import key_players, pipeline_summary, synthetic_trials

HERE = Path(__file__).parent
OUT = HERE / "results"


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (HERE / "datasets" / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def relevant(hit: dict, row: dict) -> bool:
    return hit["metadata"]["doc_id"] in row["reference_docs"] and any(m in hit["content"] for m in row["must_contain"])


def eval_extraction() -> dict:
    s = get_settings()
    report = json.loads((s.extracted_dir / "extraction_report.json").read_text(encoding="utf-8"))
    pdf = report["CARD-GL-2026"]
    md = (s.extracted_dir / "markdown" / "CARD-GL-2026.md").read_text(encoding="utf-8")
    table_rows = [ln for ln in md.splitlines() if ln.startswith("| ")]
    checks = {
        "header_footer_removed": "NOT FOR CLINICAL USE" not in md and pdf["header_footer_lines_removed"] == 2 * pdf["pages"],
        "two_column_order": md.index("value-based care programs") < md.index("### 2. Diagnosis"),
        "table_merged_across_pages": pdf["tables_merged_across_pages"] == 1 and sum(r.startswith("| Drug class") for r in table_rows) == 1,
        "all_gdmt_rows_present": all(f"| {d} |" in md for d in ("ARNI", "Ivabradine", "sGC stimulator", "IV iron")),
        "images_with_captions": len(pdf["images"]) == 2 and all(i["caption_hint"].startswith("Figure") for i in pdf["images"]),
        "footnotes_tagged": pdf["footnotes"] == 2,
        "docx_image_extracted": report["STRAT-2026"]["images_extracted"] == 1,
    }
    captions = json.loads((s.extracted_dir / "captions.json").read_text(encoding="utf-8")) if (s.extracted_dir / "captions.json").exists() else {}
    checks["vision_captions_cached"] = len(captions) == 3
    return {"passed": sum(checks.values()), "total": len(checks), "checks": checks}


def eval_retrieval(k: int) -> dict:
    store = get_retrievers()["documents"]
    per, by_type = [], {}
    for row in load("rag_dataset.jsonl"):
        hits = store.search(row["question"], k, {"classification": ["public", "internal"]})
        ranks = [i for i, h in enumerate(hits, start=1) if relevant(h, row)]
        per.append({"question": row["question"], "source_type": row["source_type"], "hit": bool(ranks),
                    "rr": 1 / ranks[0] if ranks else 0.0, "top": [h["id"] for h in hits[:3]]})
        by_type.setdefault(row["source_type"], []).append(bool(ranks))
    return {"k": k, "hit_rate": round(statistics.mean(p["hit"] for p in per), 3), "mrr": round(statistics.mean(p["rr"] for p in per), 3),
            "by_source_type": {t: round(statistics.mean(v), 3) for t, v in by_type.items()},
            "misses": [p for p in per if not p["hit"]]}


def eval_access_control(k: int) -> dict:
    """The external consultant (public clearance) must never retrieve internal chunks, whatever they ask."""
    store = get_retrievers()["documents"]
    leaked = 0
    for row in load("rag_dataset.jsonl"):
        leaked += sum(h["metadata"]["classification"] != "public" for h in store.search(row["question"], k, {"classification": ["public"]}))
    return {"internal_chunks_returned_to_public_role": leaked}


def eval_guardrails() -> dict:
    tp = fp = fn = tn = 0
    wrong = []
    for row in load("guardrail_dataset.jsonl"):
        cat = check_input(row["text"]).category
        blocked, expected = cat is not None, row["expected"] is not None
        tp += blocked and expected
        fp += blocked and not expected
        fn += expected and not blocked
        tn += not blocked and not expected
        if cat != row["expected"]:
            wrong.append({"text": row["text"], "expected": row["expected"], "got": cat})
    return {"precision": round(tp / (tp + fp), 3) if tp + fp else 1.0, "recall": round(tp / (tp + fn), 3) if tp + fn else 1.0,
            "cases": tp + fp + fn + tn, "wrong": wrong}


def eval_registry() -> dict:
    """Analytics computed in code must match a direct count of the CSV."""
    s = get_settings()
    with open(s.data_dir / "pipeline_trials.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    out = {}
    for cond in CATALOGUE.values():
        mine = [r for r in rows if r["condition"] == cond.registry_condition and r["status"] != "Completed"]
        summary, kp = pipeline_summary(synthetic_trials(cond)), key_players(synthetic_trials(cond))
        sponsors = Counter(r["sponsor"] for r in mine if r["sponsor_type"] == "Industry")
        out[cond.key] = {"active_matches_csv": summary["active_programs"] == len(mine),
                         "modality_counts_match": summary["by_modality"] == dict(Counter(r["modality"] for r in mine)),
                         "top_company_correct": kp["companies"][0]["active_programs"] == max(sponsors.values())}
    return out


def eval_briefings(n: int) -> list[dict]:
    from medbrief.service import get_service

    results = []
    for cond, role in [("heart failure", "strategy_analyst"), ("type 2 diabetes", "external_consultant"), ("HFrEF", "executive")][:n]:
        r = get_service().brief(cond, role, "synthetic", "eval")
        b = r["briefing"] or {}
        sections = b.get("sections", {})
        results.append({"condition": cond, "role": role, "outcome": r["outcome"], "latency_s": round(r["latency_ms"] / 1000, 1),
                        "llm_written": b.get("llm_written"),
                        "sections_filled": sum(bool(v) and v != ["Not covered by the available sources."] for v in sections.values()),
                        "sections_expected": len(sections),
                        "bullets_with_citation": round(statistics.mean(["[" in x for v in sections.values() for x in v] or [0]), 3),
                        "output_issues": r["guardrail"].get("output_issues")})
        print(results[-1], flush=True)
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefings", type=int, default=0, help="number of end-to-end LLM briefings to run")
    args = ap.parse_args()
    ensure_index()
    k = get_settings().top_k
    report = {"extraction": eval_extraction(), "retrieval": eval_retrieval(k), "access_control": eval_access_control(k),
              "guardrails": eval_guardrails(), "registry_analytics": eval_registry()}
    if args.briefings:
        report["briefings"] = eval_briefings(args.briefings)
    OUT.mkdir(exist_ok=True)
    (OUT / "eval_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for name, section in report.items():
        print(f"\n== {name}\n{json.dumps(section, indent=1)[:1500]}")


if __name__ == "__main__":
    main()
