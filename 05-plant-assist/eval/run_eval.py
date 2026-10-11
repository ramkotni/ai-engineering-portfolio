"""Offline evaluation - routing, retrieval, guardrails and (optionally) answers.

    python -m eval.run_eval --no-llm     # keyword routing + retrieval + guardrails: no chat-model calls (cheap)
    python -m eval.run_eval              # + LLM router accuracy (1 LLM call per question)
    python -m eval.run_eval --full       # + end-to-end answers: fact recall, citations, grounding, latency (slow on CPU)

Metrics
  routing      accuracy of the primary source vs. the label (LLM router and keyword fallback)
  retrieval    hit@k  - an expected document is among the chunks retrieved for the routed sources
               MRR    - 1 / rank of the first expected document (rank over fused results)
  guardrails   block precision / recall on eval/guardrail_dataset.jsonl (unsafe + injection vs legitimate)
  answers      answered rate, expected document cited, fact recall (expected key facts present),
               citation validity, numeric grounding, latency p50 / p95
Results -> eval/results.json (the deck reads it).
"""

import argparse
import json
import statistics
import time
from collections import Counter
from pathlib import Path

from plant_assist.config import get_settings
from plant_assist.guardrails import check_input
from plant_assist.ingest import ensure_index
from plant_assist.retrieval import get_retrievers
from plant_assist.router import keyword_route, llm_route, plan_retrieval
from plant_assist.sources import OUT_OF_SCOPE

HERE = Path(__file__).parent


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (HERE / name).read_text(encoding="utf-8").splitlines() if line.strip()]


def normalise(text: str) -> str:
    return " ".join(text.lower().replace(",", "").split())


def fact_recall(answer: str, facts: list[str]) -> float | None:
    if not facts:
        return None
    a = normalise(answer)
    return sum(normalise(f) in a for f in facts) / len(facts)


def evaluate_guardrails() -> dict:
    rows = load("guardrail_dataset.jsonl")
    tp = fp = fn = 0
    misses = []
    for r in rows:
        blocked = not check_input(r["question"]).allowed
        tp += blocked and r["should_block"]
        fp += blocked and not r["should_block"]
        fn += (not blocked) and r["should_block"]
        if blocked != r["should_block"]:
            misses.append(r["question"])
    return {
        "cases": len(rows),
        "block_precision": round(tp / (tp + fp), 3) if tp + fp else 1.0,
        "block_recall": round(tp / (tp + fn), 3) if tp + fn else 1.0,
        "misclassified": misses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="keyword routing only - no chat-model calls")
    parser.add_argument("--full", action="store_true", help="also run the whole graph per question")
    parser.add_argument("--limit", type=int, default=0, help="evaluate only the first N questions")
    args = parser.parse_args()

    s = get_settings()
    ensure_index()
    retrievers = get_retrievers()
    llm = None
    if not args.no_llm:
        from plant_assist.llm import get_chat_model

        llm = get_chat_model()
    assistant = None
    if args.full:
        from plant_assist.service import PlantAssistant

        assistant = PlantAssistant()

    rows = load("routing_dataset.jsonl")[: args.limit or None]
    results = []
    for row in rows:
        q, expected = row["question"], row["expected_source"]
        kw = keyword_route(q)
        t0 = time.perf_counter()
        if llm is not None:
            try:
                decision = llm_route(llm, q)
            except Exception:  # noqa: BLE001 - count a router failure as the fallback decision
                decision = kw
        else:
            decision = kw
        route_ms = int((time.perf_counter() - t0) * 1000)

        # Retrieval: rank of the first expected document across all routed sources (fused by RRF).
        targets = plan_retrieval(decision, q, False, s.route_confidence_threshold)
        hits = sorted((h for t in targets for h in retrievers[t.source].search(t.query, s.top_k)),
                      key=lambda h: h["rrf"], reverse=True)
        ranked_docs = list(dict.fromkeys(h["doc_id"] for h in hits))
        rank = next((i + 1 for i, d in enumerate(ranked_docs) if d in row["expected_docs"]), None)

        rec = {
            **row,
            "router": "llm" if llm is not None else "keyword",
            "predicted_source": decision.primary_source,
            "confidence": decision.confidence,
            "keyword_route": kw.primary_source,
            "searched": [t.source for t in targets],
            "retrieval_hit": (rank is not None) if row["expected_docs"] else None,
            "reciprocal_rank": (1 / rank if rank else 0.0) if row["expected_docs"] else None,
            "route_ms": route_ms,
        }
        if assistant is not None:
            out = assistant.ask(q, channel="eval")
            issues = out["guardrail"].get("output_issues", [])
            rec |= {
                "outcome": out["outcome"],
                "cited_expected_doc": bool({c["doc_id"] for c in out["citations"]} & set(row["expected_docs"]))
                if row["expected_docs"] else None,
                "fact_recall": fact_recall(out["answer"], row["expected_facts"]),
                "citations_valid": not any(i.startswith(("invalid_citation", "no_citations")) for i in issues),
                "numbers_grounded": not any(i.startswith("unsupported_numbers") for i in issues),
                "grounded": out["grounded"],
                "latency_ms": out["latency_ms"],
            }
        results.append(rec)
        mark = "OK " if rec["predicted_source"] == expected else "XX "
        print(f"{mark}{expected:12s} -> {rec['predicted_source']:12s} hit={rec['retrieval_hit']!s:5s} {q}")

    n = len(results)
    in_scope = [r for r in results if r["expected_docs"]]
    rr = [r["reciprocal_rank"] for r in in_scope]
    summary = {
        "mode": "full" if args.full else ("keyword" if args.no_llm else "llm"),
        "questions": n,
        "model": None if args.no_llm else (s.ollama_chat_model if s.llm_provider == "ollama" else s.bedrock_model_id),
        "routing_accuracy": round(sum(r["predicted_source"] == r["expected_source"] for r in results) / n, 3),
        "keyword_router_accuracy": round(sum(r["keyword_route"] == r["expected_source"] for r in results) / n, 3),
        "per_source_accuracy": {
            src: round(sum(r["predicted_source"] == src for r in results if r["expected_source"] == src)
                       / cnt, 3)
            for src, cnt in Counter(r["expected_source"] for r in results).items()
        },
        "out_of_scope_detected": sum(r["predicted_source"] == OUT_OF_SCOPE for r in results if r["expected_source"] == OUT_OF_SCOPE),
        "retrieval_hit_rate": round(sum(bool(r["retrieval_hit"]) for r in in_scope) / len(in_scope), 3),
        "mrr": round(sum(rr) / len(rr), 3),
        "avg_route_ms": int(sum(r["route_ms"] for r in results) / n),
        "guardrails": evaluate_guardrails(),
    }
    if args.full:
        lat = sorted(r["latency_ms"] for r in results)
        recalls = [r["fact_recall"] for r in in_scope if r["fact_recall"] is not None]
        summary["answers"] = {
            "answered_rate": round(sum(r["outcome"] == "answered" for r in in_scope) / len(in_scope), 3),
            "cited_expected_doc_rate": round(sum(bool(r["cited_expected_doc"]) for r in in_scope) / len(in_scope), 3),
            "fact_recall": round(statistics.mean(recalls), 3) if recalls else None,
            "citations_valid_rate": round(sum(r["citations_valid"] for r in results) / n, 3),
            "numbers_grounded_rate": round(sum(r["numbers_grounded"] for r in results) / n, 3),
            "latency_p50_ms": int(statistics.median(lat)),
            "latency_p95_ms": lat[min(len(lat) - 1, int(0.95 * len(lat)))],
        }

    (HERE / "results.json").write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
