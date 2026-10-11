"""Run the golden-dataset evaluation as a LangSmith *experiment*.

Why, on top of eval/run_eval.py: LangSmith keeps every experiment, so runs can
be compared side by side (llama3.2 vs Claude, prompt v1 vs v2), and each score
links to the full trace of the run that produced it.

    python -m eval.langsmith_eval                 # sync dataset + run experiment
    python -m eval.langsmith_eval --limit 4       # quick run on the first 4 examples
    python -m eval.langsmith_eval --judge         # add the LLM-as-judge evaluator
    python -m eval.langsmith_eval --recreate      # re-upload the dataset after editing the JSONL

Needs LANGSMITH_TRACING=true and LANGSMITH_API_KEY in .env.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid

from app.config import get_settings
from app.observability import configure_tracing
from eval.run_eval import DATASET, judge, score_case

DATASET_NAME = "evergreen-member-assist-golden"
METRIC_KEYS = ("guardrail_correct", "intent_correct", "retrieval_hit", "reciprocal_rank", "keyword_recall",
               "leakage_free", "expected_flags_present")


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def to_example(case: dict) -> dict:
    """Golden case -> LangSmith example: inputs are what the app receives, outputs are the expectations."""
    inputs = {"question": case["question"], "member_id": case.get("member_id")}
    outputs = {k: v for k, v in case.items() if k not in ("question", "member_id", "id", "category")}
    return {"inputs": inputs, "outputs": outputs, "metadata": {"case_id": case["id"], "category": case["category"]}}


def sync_dataset(client, recreate: bool = False) -> str:
    if client.has_dataset(dataset_name=DATASET_NAME):
        if not recreate:
            print(f"Dataset '{DATASET_NAME}' exists (use --recreate after editing the golden set)")
            return DATASET_NAME
        client.delete_dataset(dataset_name=DATASET_NAME)
    client.create_dataset(DATASET_NAME, description="Evergreen Member Assist golden set (policy, claims, authZ, guardrails)")
    client.create_examples(dataset_name=DATASET_NAME, examples=[to_example(c) for c in load_cases()])
    print(f"Uploaded {len(load_cases())} examples to '{DATASET_NAME}'")
    return DATASET_NAME


def deterministic_metrics(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
    """LangSmith evaluator: the same scoring as eval/run_eval.py, one feedback key per metric."""
    scores = score_case(
        reference_outputs, outputs.get("answer", ""), outputs.get("intent"), outputs.get("blocked", False),
        outputs.get("flags", []), outputs.get("retrieved_sources", []),
    )
    return {"results": [{"key": k, "score": float(scores[k])} for k in METRIC_KEYS if k in scores]}


def make_target(service):
    """Wrap AgentService so LangSmith can call it with an example's inputs."""
    from app.service import ChatRequest

    def target(inputs: dict) -> dict:
        session = f"ls-eval-{uuid.uuid4().hex[:10]}"
        resp = service.ask(ChatRequest(question=inputs["question"], member_id=inputs.get("member_id"), session_id=session))
        state = service.graph.get_state({"configurable": {"thread_id": session}}).values
        from app.graph.nodes import _build_context

        return {
            "answer": resp.answer, "intent": resp.intent, "blocked": resp.guardrail.get("blocked", False),
            "flags": resp.guardrail.get("flags", []), "trace": resp.trace, "latency_ms": resp.latency_ms,
            "retrieved_sources": [d["source"] for d in state.get("documents", [])],
            "context": _build_context(state),
        }

    return target


def make_judge_evaluator(judge_llm):
    def llm_judge(inputs: dict, outputs: dict, reference_outputs: dict) -> dict:
        if reference_outputs.get("should_block"):
            return {"results": []}
        case = {"question": inputs["question"], "reference_answer": reference_outputs.get("reference_answer", "(none)")}
        s = judge(judge_llm, case, outputs.get("answer", ""), outputs.get("context", ""))
        if s is None:
            return {"results": []}
        return {"results": [{"key": "faithfulness", "score": s.faithfulness / 5, "comment": s.reasoning},
                            {"key": "relevance", "score": s.relevance / 5},
                            {"key": "correctness", "score": s.correctness / 5}]}

    return llm_judge


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int)
    p.add_argument("--judge", action="store_true", help="add LLM-as-judge (EVAL_JUDGE_* settings)")
    p.add_argument("--recreate", action="store_true")
    args = p.parse_args()

    s = get_settings()
    if not configure_tracing(s):
        print("LangSmith is not configured: set LANGSMITH_TRACING=true and LANGSMITH_API_KEY in .env", file=sys.stderr)
        return 2

    from langsmith import Client, evaluate

    from app.service import AgentService

    client = Client()
    name = sync_dataset(client, recreate=args.recreate)
    data = list(client.list_examples(dataset_name=name, limit=args.limit)) if args.limit else name

    evaluators = [deterministic_metrics]
    if args.judge:
        from app.providers import get_judge_model

        evaluators.append(make_judge_evaluator(get_judge_model(s)))

    model = s.ollama_chat_model if s.llm_provider == "ollama" else s.bedrock_chat_model_id
    results = evaluate(
        make_target(AgentService.from_settings(s)),
        data=data,
        evaluators=evaluators,
        experiment_prefix=f"{s.llm_provider}-{model.split(':')[0]}-{s.groundedness_mode}",
        metadata={"model": model, "llm_provider": s.llm_provider, "groundedness_mode": s.groundedness_mode,
                  "relevance_threshold": s.relevance_threshold, "app_version": s.app_version},
        max_concurrency=1,  # local CPU model; raise for Bedrock
        client=client,
    )
    print(f"\nExperiment: {results.experiment_name}  (open the dataset in LangSmith to compare experiments)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
