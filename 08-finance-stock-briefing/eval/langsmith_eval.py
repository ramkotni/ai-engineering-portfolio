"""Run the follow-up QA dataset as a LangSmith experiment (requires LANGSMITH_API_KEY in .env).

    python -m eval.langsmith_eval [--limit 5]
"""

import argparse
import json
import os
from pathlib import Path

DATASET = "stockbrief-qa-eval"
HERE = Path(__file__).parent


def doc_cited(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "expected_doc_cited", "score": int(bool(set(outputs.get("cited_docs", [])) & set(reference_outputs["reference_docs"])))}


def reference_overlap(outputs: dict, reference_outputs: dict) -> dict:
    """Share of the reference answer's key terms (numbers and words of 5+ letters) present in the answer."""
    import re

    terms = {t.lower() for t in re.findall(r"\d+(?:[./]\d+)?%?|[A-Za-z]{5,}", reference_outputs["reference"])}
    a = outputs.get("answer", "").lower()
    return {"key": "reference_term_recall", "score": round(sum(t in a for t in terms) / len(terms), 3) if terms else None}


def output_guard_clean(outputs: dict) -> dict:
    return {"key": "output_guard_clean", "score": int(not outputs.get("output_issues"))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    from stockbrief.observability import configure_tracing

    configure_tracing()
    if not (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")):
        raise SystemExit("Set LANGSMITH_API_KEY and LANGSMITH_TRACING=true in .env first.")
    from langsmith import Client, evaluate

    from stockbrief.ingest import ensure_index
    from stockbrief.service import get_service

    client = Client()
    if not client.has_dataset(dataset_name=DATASET):
        rows = [json.loads(line) for line in (HERE / "datasets" / "rag_dataset.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
        ds = client.create_dataset(DATASET, description="Stock briefing follow-up QA evaluation")
        client.create_examples(dataset_id=ds.id, examples=[
            {"inputs": {"question": r["question"]}, "outputs": {"reference_docs": r["reference_docs"], "reference": r["reference"]}}
            for r in rows])
    ensure_index()

    def target(inputs: dict) -> dict:
        r = get_service().ask(inputs["question"], "research_analyst", "synthetic", "eval")
        return {"cited_docs": sorted({c["doc_id"] for c in r["citations"]}), "answer": r["answer"],
                "output_issues": r["guardrail"].get("output_issues", [])}

    examples = list(client.list_examples(dataset_name=DATASET))[: args.limit or None]
    evaluate(target, data=examples, evaluators=[doc_cited, reference_overlap, output_guard_clean],
             experiment_prefix="stockbrief", max_concurrency=1)


if __name__ == "__main__":
    main()
