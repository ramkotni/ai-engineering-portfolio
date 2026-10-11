"""RAGAS evaluation and retrieval optimisation for PlantAssist.

    python -m eval.ragas_eval --optimize       # non-LLM RAGAS context precision / recall + sweep (embeddings only)
    python -m eval.ragas_eval --llm 2          # + LLM-judged faithfulness / groundedness / context recall

Retrieval is evaluated given the correct source (so routing errors do not mask retrieval quality).
Reference contexts = all chunks of the documents labelled as containing the answer.
"""

import argparse
import json
import statistics
from pathlib import Path

from eval.ragas_utils import judge_llm, llm_scores, non_llm_scores
from plant_assist.config import get_settings
from plant_assist.ingest import ensure_index, load_source_documents
from plant_assist.retrieval import get_retrievers
from plant_assist.sources import SOURCES

HERE = Path(__file__).parent
OUT = HERE / "results"


def rows() -> list[dict]:
    data = [json.loads(line) for line in (HERE / "routing_dataset.jsonl").read_text().splitlines() if line.strip()]
    return [r for r in data if r["expected_docs"]]


def chunks_by_doc() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for src in SOURCES.values():
        for d in load_source_documents(src):
            out.setdefault(d.metadata["doc_id"], []).append(d.page_content)
    return out


def retrieve(question: str, source: str, k: int, mode: str) -> list[str]:
    r = get_retrievers()[source]
    if mode == "hybrid":
        return [h["content"] for h in r.search(question, k)]
    if mode == "vector":
        return [d.page_content for d, _ in r.store.similarity_search_with_relevance_scores(question, k=k)]
    bm25 = r._lexical_index()
    scores = bm25.scores(question)
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [r._corpus[i][1] for i in order]


def evaluate(data, refs, k: int, mode: str) -> dict:
    per = [non_llm_scores(r["question"], retrieve(r["question"], r["expected_source"], k, mode),
                          [c for d in r["expected_docs"] for c in refs.get(d, [])]) for r in data]
    p = statistics.mean(x["context_precision"] for x in per)
    rc = statistics.mean(x["context_recall"] for x in per)
    return {"mode": mode, "top_k": k, "context_precision": round(p, 3), "context_recall": round(rc, 3),
            "f1": round(2 * p * rc / (p + rc), 3) if p + rc else 0.0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--optimize", action="store_true")
    ap.add_argument("--llm", type=int, default=0)
    args = ap.parse_args()
    OUT.mkdir(exist_ok=True)
    ensure_index()
    s = get_settings()
    data, refs = rows(), chunks_by_doc()
    report = {"baseline": evaluate(data, refs, s.top_k, "hybrid")}
    print("baseline:", report["baseline"], flush=True)
    if args.optimize:
        grid = [evaluate(data, refs, k, mode) for mode in ("vector", "bm25", "hybrid") for k in (3, 5, 8)]
        best = max(grid, key=lambda g: g["f1"])
        current = next(g for g in grid if g["mode"] == "hybrid" and g["top_k"] == s.top_k)
        hybrid_best = max((g for g in grid if g["mode"] == "hybrid"), key=lambda g: g["f1"])
        if best["f1"] - current["f1"] < 0.01:
            best = {**current, "note": "best alternative within 0.01 F1 of current settings - keep current"}
        elif best["f1"] - hybrid_best["f1"] < 0.01:
            best = {**hybrid_best, "note": "vector-only within 0.01 F1 of hybrid - prefer hybrid for exact-term matching"}
        report |= {"sweep": grid, "recommended": best}
        for g in grid:
            print(g, flush=True)
        print("recommended:", best, flush=True)
    if args.llm:
        from plant_assist.service import get_assistant

        judge, judged = judge_llm(), []
        for r in data[: args.llm]:
            out = get_assistant().ask(r["question"], "eval", "floor_supervisor")
            ref = "; ".join(r.get("expected_facts", [])) or r["question"]
            sc = llm_scores(judge, r["question"], out["answer"], out["contexts"] or [""], ref)
            judged.append({"question": r["question"], **sc, "latency_ms": out["latency_ms"]})
            print(judged[-1], flush=True)
        report["llm_judged"] = judged
    (OUT / "ragas_report.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
