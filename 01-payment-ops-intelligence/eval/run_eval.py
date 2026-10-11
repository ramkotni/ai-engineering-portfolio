"""Offline evaluation (no LLM unless --llm).

    python -m eval.run_eval            # intent (keyword fallback), retrieval hit@k / MRR, guardrails, analytics checks
    python -m eval.run_eval --llm      # + Intent Agent accuracy with the LLM (1 call per question)

Results -> eval/results/eval_report.json
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from payops import analytics
from payops.agents import keyword_intent
from payops.config import get_settings
from payops.guardrails import check_input
from payops.ingest import ensure_index
from payops.retrieval import get_retrievers

HERE = Path(__file__).parent


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (HERE / "datasets" / name).read_text().splitlines() if line.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    args = ap.parse_args()
    (HERE / "results").mkdir(exist_ok=True)
    report: dict = {}

    # 1. Intent classification
    rows = load("intent_dataset.jsonl")
    agents = None
    if args.llm:
        from payops.agents import PaymentAgents
        from payops.llm import get_chat_model

        agents = PaymentAgents(get_chat_model(), {}, get_settings())
    correct = cat_correct = 0
    for r in rows:
        d = agents.classify(r["question"])[0] if agents else keyword_intent(r["question"])
        correct += d.intent == r["intent"]
        cat_correct += d.category == r["category"]
    report["intent"] = {"mode": "llm" if args.llm else "keyword", "questions": len(rows),
                        "accuracy": round(correct / len(rows), 3), "category_accuracy": round(cat_correct / len(rows), 3)}

    # 2. Retrieval: is an incident of the expected category retrieved, and how high?
    ensure_index()
    inc = get_retrievers()["incidents"]
    rag = [r for r in load("rag_dataset.jsonl") if r["category"]]
    hits, rr, precision = 0, [], []
    k = get_settings().search_top_k
    for r in rag:
        got = [h["metadata"]["failure_category"] for h in inc.search(r["question"], k)]
        rank = next((i + 1 for i, c in enumerate(got) if c == r["category"]), None)
        hits += rank is not None
        rr.append(1 / rank if rank else 0)
        precision.append(sum(c == r["category"] for c in got) / len(got))
    report["retrieval"] = {"questions": len(rag), "top_k": k, "hit_rate": round(hits / len(rag), 3),
                           "mrr": round(sum(rr) / len(rr), 3), "precision_at_k": round(sum(precision) / len(precision), 3)}

    # 3. Guardrails
    g = load("guardrail_dataset.jsonl")
    tp = sum((not check_input(r["question"]).allowed) and r["should_block"] for r in g)
    fp = sum((not check_input(r["question"]).allowed) and not r["should_block"] for r in g)
    fn = sum(check_input(r["question"]).allowed and r["should_block"] for r in g)
    report["guardrails"] = {"cases": len(g), "block_precision": round(tp / (tp + fp), 3) if tp + fp else 1.0,
                            "block_recall": round(tp / (tp + fn), 3) if tp + fn else 1.0}

    # 4. Analytics correctness vs an independent pandas computation
    df = pd.read_csv(get_settings().data_dir / "incidents.csv")
    checks = []
    for cat in df.failure_category.unique():
        rep = analytics.trend_report(category=cat)
        checks.append(rep["incidents"] == int((df.failure_category == cat).sum()))
    report["analytics"] = {"checks": len(checks), "passed": sum(checks),
                           "duplicate_trend_detected": analytics.trend_report(category="duplicate_payment")["direction"] == "rising"}

    (HERE / "results" / "eval_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
