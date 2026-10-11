"""RAGAS evaluation and retrieval optimisation over the filings index.

    python -m eval.ragas_eval                 # non-LLM RAGAS context precision / recall per question
    python -m eval.ragas_eval --optimize      # + sweep retrieval mode x top_k and recommend the best setting
    python -m eval.ragas_eval --llm 2         # + LLM-judged faithfulness / groundedness / context recall on 2 answers

Reference contexts = chunks of the reference filing that contain the must-contain fact. Retrieval is always
filtered to the question's ticker, as in the workflow. Results -> eval/results/ragas_report.json
"""

import argparse
import json
import statistics
from pathlib import Path

from eval.ragas_utils import judge_llm, llm_scores, non_llm_scores
from stockbrief.config import get_settings
from stockbrief.ingest import all_synthetic_chunks, ensure_index
from stockbrief.llm import get_embeddings
from stockbrief.retrieval import BM25, _cos, get_retrievers

HERE = Path(__file__).parent
OUT = HERE / "results"


def load_rows() -> list[dict]:
    return [json.loads(line) for line in (HERE / "datasets" / "rag_dataset.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def references(row: dict, chunks) -> list[str]:
    return [c.page_content for c in chunks if c.metadata["doc_id"] in row["reference_docs"] and any(m in c.page_content for m in row["must_contain"])]


def retrieve(row: dict, k: int, mode: str) -> list[str]:
    store = get_retrievers()["filings"]
    if mode.startswith("hybrid"):      # "hybrid" = configured weight, "hybrid_w2" = BM25 ranking counted twice
        weight = float(mode.split("_w")[1]) if "_w" in mode else None
        return [h["content"] for h in store.search(row["question"], k, {"ticker": row["ticker"]}, bm25_weight=weight)]
    corpus = [c for c in store._load() if c[2]["ticker"] == row["ticker"]]
    if mode == "vector":
        qv = get_embeddings().embed_query(row["question"])
        order = sorted(corpus, key=lambda c: _cos(qv, c[3]), reverse=True)
    else:
        scores = BM25([c[1] for c in corpus]).scores(row["question"])
        order = [c for c, _ in sorted(zip(corpus, scores), key=lambda t: t[1], reverse=True)]
    return [c[1] for c in order[:k]]


def evaluate_config(rows, chunks, k: int, mode: str) -> dict:
    per = [non_llm_scores(r["question"], retrieve(r, k, mode), references(r, chunks)) for r in rows]
    return {"top_k": k, "mode": mode, "context_precision": round(statistics.mean(p["context_precision"] for p in per), 3),
            "context_recall": round(statistics.mean(p["context_recall"] for p in per), 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--optimize", action="store_true")
    ap.add_argument("--llm", type=int, default=0)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    ensure_index()
    s = get_settings()
    rows, chunks = load_rows(), all_synthetic_chunks()
    report = {"baseline": evaluate_config(rows, chunks, s.top_k, "hybrid")}
    print("baseline (current settings):", report["baseline"], flush=True)

    if args.optimize:
        grid = [evaluate_config(rows, chunks, k, mode) for mode in ("vector", "bm25", "hybrid_w1", "hybrid_w2", "hybrid_w3") for k in (3, 6, 10)]
        for g in grid:
            p, r = g["context_precision"], g["context_recall"]
            g["f1"] = round(2 * p * r / (p + r), 3) if p + r else 0.0
        best = max(grid, key=lambda g: g["f1"])
        current = next(g for g in grid if g["mode"] == f"hybrid_w{s.bm25_weight:g}" and g["top_k"] == s.top_k)
        hybrid_best = max((g for g in grid if g["mode"].startswith("hybrid")), key=lambda g: g["f1"])
        if best["f1"] - current["f1"] < 0.01:
            best = {**current, "note": "best alternative within 0.01 F1 of current settings - keep current"}
        elif best["f1"] - hybrid_best["f1"] < 0.01:
            best = {**hybrid_best, "note": "within 0.01 F1 of the best hybrid setting - prefer hybrid (keeps semantic matching for paraphrased questions)"}
        report |= {"sweep": grid, "recommended": best}
        print("\nmode    top_k  ctx_precision  ctx_recall  f1")
        for g in grid:
            print(f"{g['mode']:9s} {g['top_k']:5d}  {g['context_precision']:13.3f}  {g['context_recall']:10.3f}  {g['f1']:.3f}")
        print("recommended:", best)

    if args.llm:
        from stockbrief.service import get_service

        judge, judged = judge_llm(), []
        for row in rows[: args.llm]:
            r = get_service().ask(row["question"], "research_analyst", "synthetic", "eval")
            scores = llm_scores(judge, row["question"], r["answer"], r["contexts"], row["reference"])
            scores |= non_llm_scores(row["question"], r["contexts"], references(row, chunks), r["answer"], row["reference"])
            judged.append({"question": row["question"], **scores, "latency_ms": r["latency_ms"]})
            print(judged[-1], flush=True)
        report["llm_judged"] = judged

    previous = OUT / "ragas_report.json"     # merge: an --llm run keeps the last sweep and vice versa
    merged = (json.loads(previous.read_text(encoding="utf-8")) if previous.exists() else {}) | report
    previous.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"\nWrote {OUT / 'ragas_report.json'}")


if __name__ == "__main__":
    main()
