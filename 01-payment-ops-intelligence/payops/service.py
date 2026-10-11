"""Single entry point used by the API, CLI, UI and evaluation."""

import time
import uuid
from functools import lru_cache

from payops import rbac
from payops.graph import build_graph
from payops.observability import configure_tracing, record_feedback, record_request, run_config


class PaymentOpsAssistant:
    def __init__(self, graph=None):
        self.tracing = configure_tracing()
        self.graph = graph or build_graph()

    def ask(self, question: str, role: str, channel: str = "api") -> dict:
        rbac.get_role(role)  # raises KeyError for unknown roles
        run_id = uuid.uuid4()
        start = time.perf_counter()
        state = self.graph.invoke({"question": question, "role": role}, config=run_config(run_id, role, channel))
        result = {
            "run_id": str(run_id),
            "role": role,
            "question": state["question"],
            "answer": state.get("answer", ""),
            "outcome": state.get("outcome", ""),
            "intent": state.get("intent", {}),
            "plan": state.get("plan", []),
            "citations": state.get("citations", []),
            "guardrail": state.get("guardrail", {}),
            "contexts": _contexts(state.get("outputs", {})),
            "trace": state.get("trace", []),
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
        record_request(result)
        return result

    @staticmethod
    def feedback(run_id: str, score: int, comment: str | None = None) -> dict:
        return record_feedback(run_id, score, comment)


def _contexts(outputs: dict) -> list[str]:
    """Retrieved evidence, exposed for RAGAS evaluation and the UI."""
    ctx = [h["content"] for h in outputs.get("search", {}).get("incidents", [])]
    ctx += [k["content"] for k in outputs.get("search", {}).get("knowledge", [])]
    ctx += [r["content"] for r in outputs.get("recommendation", {}).get("rules", [])]
    if "trend" in outputs:
        ctx.append(outputs["trend"]["evidence"])
    return ctx


@lru_cache
def get_assistant() -> PaymentOpsAssistant:
    return PaymentOpsAssistant()
