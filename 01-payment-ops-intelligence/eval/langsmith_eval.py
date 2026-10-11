"""Run the intent dataset as a LangSmith experiment (requires LANGSMITH_API_KEY in .env).

    python -m eval.langsmith_eval [--limit 5]
"""

import argparse
import json
import os
from pathlib import Path

DATASET = "payops-intent-eval"
HERE = Path(__file__).parent


def intent_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "intent_correct", "score": int(outputs.get("intent") == reference_outputs["intent"])}


def category_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "category_correct", "score": int(outputs.get("category") == reference_outputs["category"])}


def output_guard_clean(outputs: dict) -> dict:
    return {"key": "output_guard_clean", "score": int(not outputs.get("output_issues"))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    from payops.observability import configure_tracing

    configure_tracing()
    if not (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")):
        raise SystemExit("Set LANGSMITH_API_KEY and LANGSMITH_TRACING=true in .env first.")
    from langsmith import Client, evaluate

    from payops.ingest import ensure_index
    from payops.service import get_assistant

    client = Client()
    if not client.has_dataset(dataset_name=DATASET):
        rows = [json.loads(line) for line in (HERE / "datasets" / "intent_dataset.jsonl").read_text().splitlines() if line.strip()]
        ds = client.create_dataset(DATASET, description="Payment ops intent + routing evaluation")
        client.create_examples(dataset_id=ds.id, examples=[
            {"inputs": {"question": r["question"]}, "outputs": {"intent": r["intent"], "category": r["category"]}} for r in rows])
    ensure_index()

    def target(inputs: dict) -> dict:
        r = get_assistant().ask(inputs["question"], "operations_manager", "eval")
        return {"intent": r["intent"].get("intent"), "category": r["intent"].get("category"), "answer": r["answer"],
                "output_issues": r["guardrail"].get("output_issues", [])}

    examples = list(client.list_examples(dataset_name=DATASET))[: args.limit or None]
    evaluate(target, data=examples, evaluators=[intent_correct, category_correct, output_guard_clean],
             experiment_prefix="payops", max_concurrency=1)


if __name__ == "__main__":
    main()
