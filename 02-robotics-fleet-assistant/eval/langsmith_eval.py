"""Run the intent dataset as a LangSmith experiment (requires LANGSMITH_API_KEY in .env).

    python -m eval.langsmith_eval [--limit 5]
"""

import argparse
import json
import os
from pathlib import Path

DATASET = "fleetops-intent-eval"
HERE = Path(__file__).parent


def intent_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "intent_correct", "score": int(outputs.get("intent") == reference_outputs["intent"])}


def robot_grounded(outputs: dict) -> dict:
    return {"key": "ids_grounded", "score": int(not any(i.startswith("unknown_ids") for i in outputs.get("output_issues", [])))}


def output_guard_clean(outputs: dict) -> dict:
    return {"key": "output_guard_clean", "score": int(not outputs.get("output_issues"))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    from fleetops.observability import configure_tracing

    configure_tracing()
    if not (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")):
        raise SystemExit("Set LANGSMITH_API_KEY and LANGSMITH_TRACING=true in .env first.")
    from langsmith import Client, evaluate

    from fleetops.ingest import ensure_index
    from fleetops.service import get_assistant

    client = Client()
    if not client.has_dataset(dataset_name=DATASET):
        rows = [json.loads(line) for line in (HERE / "datasets" / "intent_dataset.jsonl").read_text().splitlines() if line.strip()]
        ds = client.create_dataset(DATASET, description="Robotics fleet intent evaluation")
        client.create_examples(dataset_id=ds.id, examples=[
            {"inputs": {"question": r["question"]}, "outputs": {"intent": r["intent"]}} for r in rows])
    ensure_index()

    def target(inputs: dict) -> dict:
        r = get_assistant().ask(inputs["question"], "fleet_manager", "eval")
        return {"intent": r["intent"].get("intent"), "answer": r["answer"],
                "output_issues": r["guardrail"].get("output_issues", [])}

    examples = list(client.list_examples(dataset_name=DATASET))[: args.limit or None]
    evaluate(target, data=examples, evaluators=[intent_correct, robot_grounded, output_guard_clean],
             experiment_prefix="fleetops", max_concurrency=1)


if __name__ == "__main__":
    main()
