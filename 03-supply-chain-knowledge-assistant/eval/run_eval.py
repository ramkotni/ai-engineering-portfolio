"""Offline evaluation.   python -m eval.run_eval

retrieval hit@k / MRR per source type (text, table, image, record), access-control leakage,
guardrail precision / recall, and summarisation ROUGE-L (with --summaries, uses the LLM).
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from supplykb import rbac
from supplykb.config import get_settings
from supplykb.guardrails import check_input
from supplykb.ingest import ensure_index
from supplykb.retrieval import get_retrievers

HERE = Path(__file__).parent


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (HERE / "datasets" / name).read_text().splitlines() if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summaries", action="store_true", help="also score summaries with ROUGE-L (calls the LLM)")
    args = ap.parse_args()
    (HERE / "results").mkdir(exist_ok=True)
    ensure_index()
    store = get_retrievers()["documents"]
    k = get_settings().top_k
    qa = rbac.get_role("quality_assurance")
    report: dict = {}

    rows = load("rag_dataset.jsonl")
    per_type: dict[str, list] = defaultdict(list)
    for r in rows:
        hits = store.search(r["question"], k, {"classification": qa.visible_levels})
        docs = [h["metadata"]["doc_id"] for h in hits]
        rank = next((i + 1 for i, d in enumerate(docs) if d in r["reference_docs"]), None)
        image_hit = any(h["metadata"]["content_type"] == "image" for h in hits) if r["source_type"] == "image" else None
        per_type[r["source_type"]].append((rank, image_hit))
    all_ranks = [x[0] for v in per_type.values() for x in v]
    report["retrieval"] = {
        "questions": len(rows), "top_k": k,
        "hit_rate": round(sum(r is not None for r in all_ranks) / len(all_ranks), 3),
        "mrr": round(sum(1 / r for r in all_ranks if r) / len(all_ranks), 3),
        "by_source_type": {t: round(sum(x[0] is not None for x in v) / len(v), 3) for t, v in per_type.items()},
        "image_chunk_retrieved_for_figure_questions": round(
            sum(bool(x[1]) for x in per_type.get("image", [])) / max(len(per_type.get("image", [])), 1), 3),
    }

    # Access control: a public-clearance role must never receive internal / confidential chunks.
    partner = rbac.get_role("logistics_partner")
    leaked = 0
    for r in rows:
        leaked += sum(h["metadata"]["classification"] != "public"
                      for h in store.search(r["question"], k, {"classification": partner.visible_levels}))
    report["access_control"] = {"queries": len(rows), "restricted_chunks_returned_to_partner": leaked}

    g = load("guardrail_dataset.jsonl")
    blocked = [not check_input(r["question"]).allowed for r in g]
    tp = sum(b and r["should_block"] for b, r in zip(blocked, g))
    fp = sum(b and not r["should_block"] for b, r in zip(blocked, g))
    fn = sum((not b) and r["should_block"] for b, r in zip(blocked, g))
    report["guardrails"] = {"cases": len(g), "block_precision": round(tp / (tp + fp), 3) if tp + fp else 1.0,
                            "block_recall": round(tp / (tp + fn), 3) if tp + fn else 1.0}

    if args.summaries:
        from eval.ragas_utils import RougeScore
        from supplykb.service import get_assistant

        ref = ("Lot LOT-24117 shipped on SHP-88213 was held on the tarmac in Memphis during a flight delay and spent "
               "3 h 20 min above 8 C with a 12.6 C peak; it was quarantined, passed a QA stability review and was released "
               "on 22 August 2026. CAPA-2026-031 added carrier re-training and +20% coolant on summer lanes.")
        out = get_assistant().ask("Summarize DEV-2026-014", "quality_assurance", "eval", "summarize", "DEV-2026-014", "brief")
        report["summarization"] = {"doc": "DEV-2026-014",
                                   "rouge_l": round(float(RougeScore().score(reference=ref, response=out["answer"]).value), 3),
                                   "output_issues": out["guardrail"].get("output_issues", [])}

    (HERE / "results" / "eval_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
