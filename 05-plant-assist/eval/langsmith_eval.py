"""Run the labelled question set as a LangSmith experiment.

    LANGSMITH_API_KEY=... python -m eval.langsmith_eval [--limit N]

Creates (once) the dataset "plant-assist-eval" from eval/routing_dataset.jsonl, then runs the
full PlantAssist graph on every example. Each run is traced, and scored by the evaluators below,
so experiments (e.g. llama3.2 vs Claude, chunk_size 600 vs 900) can be compared side by side in
the LangSmith UI.
"""

import argparse
import json
import os
from pathlib import Path

DATASET = "plant-assist-eval"
HERE = Path(__file__).parent


# ---------------------------------------------------------------- evaluators
def route_correct(outputs: dict, reference_outputs: dict) -> dict:
    return {"key": "route_correct", "score": int(outputs["primary_source"] == reference_outputs["expected_source"])}


def expected_doc_cited(outputs: dict, reference_outputs: dict) -> dict:
    expected = set(reference_outputs["expected_docs"])
    if not expected:  # out-of-scope questions: correct if nothing is cited
        return {"key": "expected_doc_cited", "score": int(not outputs["cited_docs"])}
    return {"key": "expected_doc_cited", "score": int(bool(expected & set(outputs["cited_docs"])))}


def fact_recall(outputs: dict, reference_outputs: dict) -> dict:
    facts = reference_outputs["expected_facts"]
    if not facts:
        return {"key": "fact_recall", "score": None}
    answer = " ".join(outputs["answer"].lower().replace(",", "").split())
    found = sum(" ".join(f.lower().replace(",", "").split()) in answer for f in facts)
    return {"key": "fact_recall", "score": found / len(facts)}


def numbers_grounded(outputs: dict) -> dict:
    issues = outputs["guardrail"].get("output_issues", [])
    return {"key": "numbers_grounded", "score": int(not any(i.startswith("unsupported_numbers") for i in issues))}


# ---------------------------------------------------------------- run
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    from plant_assist.observability import configure_tracing

    configure_tracing()
    if not (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")):
        raise SystemExit("Set LANGSMITH_API_KEY (and LANGSMITH_TRACING=true) in .env first.")

    from langsmith import Client, evaluate

    from plant_assist.config import get_settings
    from plant_assist.ingest import ensure_index
    from plant_assist.service import PlantAssistant

    client = Client()
    if not client.has_dataset(dataset_name=DATASET):
        rows = [json.loads(line) for line in (HERE / "routing_dataset.jsonl").read_text().splitlines() if line.strip()]
        dataset = client.create_dataset(DATASET, description="PlantAssist routing + answer evaluation set")
        client.create_examples(
            dataset_id=dataset.id,
            examples=[{"inputs": {"question": r["question"]},
                       "outputs": {k: r[k] for k in ("expected_source", "expected_docs", "expected_facts")}}
                      for r in rows],
        )

    ensure_index()
    assistant = PlantAssistant()

    def target(inputs: dict) -> dict:
        r = assistant.ask(inputs["question"], channel="eval")
        return {
            "answer": r["answer"],
            "outcome": r["outcome"],
            "primary_source": r["route"].get("primary_source", r["outcome"]),
            "cited_docs": sorted({c["doc_id"] for c in r["citations"]}),
            "guardrail": r["guardrail"],
        }

    s = get_settings()
    examples = list(client.list_examples(dataset_name=DATASET))[: args.limit or None]
    evaluate(
        target,
        data=examples,
        evaluators=[route_correct, expected_doc_cited, fact_recall, numbers_grounded],
        experiment_prefix=f"plant-assist-{s.llm_provider}",
        metadata={"llm_provider": s.llm_provider, "chunk_size": s.chunk_size, "top_k": s.top_k},
        max_concurrency=1,  # CPU-friendly; raise for Bedrock
    )


if __name__ == "__main__":
    main()
