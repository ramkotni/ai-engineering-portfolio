"""Single entry point used by the API, CLI, UI and evaluation."""

import time
import uuid
from functools import lru_cache

from supplykb import rbac
from supplykb.graph import build_graph
from supplykb.observability import configure_tracing, record_feedback, record_request, run_config


class KnowledgeAssistant:
    def __init__(self, graph=None):
        self.tracing = configure_tracing()
        self.graph = graph or build_graph()

    def ask(self, question: str, role: str, channel: str = "api", task: str | None = None,
            doc_id: str | None = None, style: str | None = None) -> dict:
        rbac.get_role(role)  # raises KeyError for unknown roles
        run_id = uuid.uuid4()
        start = time.perf_counter()
        inputs = {"question": question, "role": role, **{k: v for k, v in
                  {"task": task, "doc_id": doc_id, "style": style}.items() if v}}
        state = self.graph.invoke(inputs, config=run_config(run_id, role, channel))
        result = {
            "run_id": str(run_id),
            "role": role,
            "question": state["question"],
            "answer": state.get("answer", ""),
            "outcome": state.get("outcome", ""),
            "intent": {"intent": state.get("task", ""), "method": "rules", "doc_id": state.get("doc_id", "")},
            "plan": [state.get("task", "")],
            "citations": state.get("citations", []),
            "guardrail": state.get("guardrail", {}),
            "contexts": _contexts(state),
            "trace": state.get("trace", []),
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
        record_request(result)
        return result

    @staticmethod
    def feedback(run_id: str, score: int, comment: str | None = None) -> dict:
        return record_feedback(run_id, score, comment)


def _contexts(state: dict) -> list[str]:
    """Context actually given to the LLM - exposed for RAGAS evaluation."""
    return [h["content"] for h in state.get("context", [])]


@lru_cache
def get_assistant() -> KnowledgeAssistant:
    return KnowledgeAssistant()
