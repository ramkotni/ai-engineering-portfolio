"""Offline evaluation.   python -m eval.run_eval [--llm]

intent accuracy (keyword fallback or LLM), retrieval hit@k / MRR / precision@k on event type,
guardrail precision / recall, and analytics checks against the planted patterns.
"""

import argparse
import json
from pathlib import Path

from fleetops import analytics
from fleetops.agents import keyword_intent
from fleetops.config import get_settings
from fleetops.guardrails import check_input
from fleetops.ingest import ensure_index
from fleetops.retrieval import get_retrievers

HERE = Path(__file__).parent


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (HERE / "datasets" / name).read_text().splitlines() if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    args = ap.parse_args()
    (HERE / "results").mkdir(exist_ok=True)
    report: dict = {}

    rows = load("intent_dataset.jsonl")
    agents = None
    if args.llm:
        from fleetops.agents import FleetAgents
        from fleetops.llm import get_chat_model

        agents = FleetAgents(get_chat_model(), {}, get_settings())
    preds = [(agents.classify(r["question"])[0] if agents else keyword_intent(r["question"])).intent for r in rows]
    report["intent"] = {"mode": "llm" if args.llm else "keyword", "questions": len(rows),
                        "accuracy": round(sum(p == r["intent"] for p, r in zip(preds, rows)) / len(rows), 3),
                        "misses": [r["question"] for p, r in zip(preds, rows) if p != r["intent"]]}

    ensure_index()
    ev = get_retrievers()["events"]
    k = get_settings().search_top_k
    rag = [r for r in load("rag_dataset.jsonl") if r["event_type"]]
    hits, rr, prec = 0, [], []
    for r in rag:
        got = [h["metadata"].get("event_type") for h in ev.search(r["question"], k)]
        rank = next((i + 1 for i, t in enumerate(got) if t == r["event_type"]), None)
        hits += rank is not None
        rr.append(1 / rank if rank else 0)
        prec.append(sum(t == r["event_type"] for t in got) / len(got))
    report["retrieval"] = {"questions": len(rag), "top_k": k, "hit_rate": round(hits / len(rag), 3),
                           "mrr": round(sum(rr) / len(rr), 3), "precision_at_k": round(sum(prec) / len(prec), 3)}

    g = load("guardrail_dataset.jsonl")
    blocked = [not check_input(r["question"]).allowed for r in g]
    tp = sum(b and r["should_block"] for b, r in zip(blocked, g))
    fp = sum(b and not r["should_block"] for b, r in zip(blocked, g))
    fn = sum((not b) and r["should_block"] for b, r in zip(blocked, g))
    report["guardrails"] = {"cases": len(g), "block_precision": round(tp / (tp + fp), 3) if tp + fp else 1.0,
                            "block_recall": round(tp / (tp + fn), 3) if tp + fn else 1.0}

    fast = {x["robot_id"] for x in analytics.battery_analysis()["flagged"] if any("fast" in f for f in x["flags"])}
    moves = analytics.rebalance()["moves"]
    report["analytics"] = {
        "fast_battery_decline_found": sorted(fast),
        "fast_battery_decline_correct": fast == {"R-1007", "R-1015", "R-1023"},
        "top_risk_robot": analytics.maintenance_risk()["top_risk"][0]["robot_id"],
        "rebalance_tasks_moved": sum(m["tasks"] for m in moves),
        "rebalance_targets_underused": sorted({m["to"] for m in moves}),
    }
    (HERE / "results" / "eval_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
