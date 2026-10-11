"""RAGAS evaluation and retrieval optimisation.

    python -m eval.ragas_eval                 # non-LLM RAGAS metrics for every question (needs embeddings only)
    python -m eval.ragas_eval --optimize      # + sweep retrieval settings and recommend the best one
    python -m eval.ragas_eval --llm 3         # + LLM-judged faithfulness / context recall on 3 end-to-end answers

Reference contexts (ground truth) come from the labelled dataset: all incidents of the expected failure
category plus the expected report / rule documents. Results -> eval/results/ragas_*.json
"""

import argparse
import json
import statistics
from pathlib import Path

from eval.ragas_utils import judge_llm, llm_scores, non_llm_scores
from payops.config import get_settings
from payops.ingest import ensure_index, incident_documents, knowledge_documents
from payops.llm import get_embeddings
from payops.retrieval import BM25, _cos, get_retrievers

HERE = Path(__file__).parent
OUT = HERE / "results"


def load_rows() -> list[dict]:
    return [json.loads(line) for line in (HERE / "datasets" / "rag_dataset.jsonl").read_text().splitlines() if line.strip()]


def references(row: dict, incidents, knowledge) -> list[str]:
    refs = [d.page_content for d in incidents if row["category"] and d.metadata["failure_category"] == row["category"]]
    refs += [d.page_content for d in knowledge if d.metadata["doc_id"] in row["reference_docs"]]
    return refs


def retrieve(question: str, k: int, mode: str) -> list[str]:
    """Retrieval exactly as the Search Agent does it, with a switchable mode for the sweep."""
    r = get_retrievers()
    if mode == "hybrid":
        hits = r["incidents"].search(question, k) + r["knowledge"].search(question, max(2, k // 2))
        return [h["content"] for h in hits]
    texts = []
    for name, kk in (("incidents", k), ("knowledge", max(2, k // 2))):
        corpus = r[name]._load()
        if mode == "vector":
            qv = get_embeddings().embed_query(question)
            order = sorted(corpus, key=lambda c: _cos(qv, c[3]), reverse=True)
        else:  # bm25
            scores = BM25([c[1] for c in corpus]).scores(question)
            order = [c for c, _ in sorted(zip(corpus, scores), key=lambda t: t[1], reverse=True)]
        texts += [c[1] for c in order[:kk]]
    return texts


def evaluate_config(rows, incidents, knowledge, k: int, mode: str) -> dict:
    per = []
    for row in rows:
        ctx = retrieve(row["question"], k, mode)
        per.append(non_llm_scores(row["question"], ctx, references(row, incidents, knowledge)))
    return {"top_k": k, "mode": mode,
            "context_precision": round(statistics.mean(p["context_precision"] for p in per), 3),
            "context_recall": round(statistics.mean(p["context_recall"] for p in per), 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--optimize", action="store_true")
    ap.add_argument("--llm", type=int, default=0, help="number of end-to-end answers to judge with an LLM")
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    ensure_index()
    s = get_settings()
    rows, incidents, knowledge = load_rows(), incident_documents(), knowledge_documents()

    baseline = evaluate_config(rows, incidents, knowledge, s.search_top_k, "hybrid")
    report = {"baseline": baseline}
    print("baseline (current settings):", baseline, flush=True)

    if args.optimize:
        grid = [evaluate_config(rows, incidents, knowledge, k, mode)
                for mode in ("vector", "bm25", "hybrid") for k in (3, 6, 10)]
        # F1 of context precision and recall picks the balanced configuration.
        for g in grid:
            p, r = g["context_precision"], g["context_recall"]
            g["f1"] = round(2 * p * r / (p + r), 3) if p + r else 0.0
        best = max(grid, key=lambda g: g["f1"])
        current = next(g for g in grid if g["mode"] == "hybrid" and g["top_k"] == s.search_top_k)
        hybrid_best = max((g for g in grid if g["mode"] == "hybrid"), key=lambda g: g["f1"])
        if best["f1"] - current["f1"] < 0.01:  # within noise on a small dataset: keep the current configuration
            best = {**current, "note": "best alternative within 0.01 F1 of current settings - keep current"}
        elif best["f1"] - hybrid_best["f1"] < 0.01:  # prefer hybrid: BM25 keeps exact IDs / codes findable
            best = {**hybrid_best, "note": "vector-only within 0.01 F1 of hybrid - prefer hybrid for exact-term matching"}
        report |= {"sweep": grid, "recommended": best}
        print("\nmode    top_k  ctx_precision  ctx_recall  f1")
        for g in grid:
            print(f"{g['mode']:7s} {g['top_k']:5d}  {g['context_precision']:13.3f}  {g['context_recall']:10.3f}  {g['f1']:.3f}")
        print("recommended:", best)

    if args.llm:
        from payops.service import get_assistant

        judge, judged = judge_llm(), []
        for row in rows[: args.llm]:
            r = get_assistant().ask(row["question"], "operations_manager", "eval")
            scores = llm_scores(judge, row["question"], r["answer"], r["contexts"], row["reference"])
            scores |= non_llm_scores(row["question"], r["contexts"], references(row, incidents, knowledge),
                                     r["answer"], row["reference"])
            judged.append({"question": row["question"], **scores, "latency_ms": r["latency_ms"]})
            print(judged[-1], flush=True)
        report["llm_judged"] = judged

    (OUT / "ragas_report.json").write_text(json.dumps(report, indent=2))
    print(f"\nWrote {OUT / 'ragas_report.json'}")


if __name__ == "__main__":
    main()
