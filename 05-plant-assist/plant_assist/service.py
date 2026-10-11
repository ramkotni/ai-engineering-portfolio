"""Thin application service shared by the CLI, REST API, Streamlit UI and AgentCore entrypoint."""

import time
import uuid
from functools import lru_cache

from plant_assist import rbac
from plant_assist.config import get_settings
from plant_assist.graph import build_graph
from plant_assist.metrics import METRICS
from plant_assist.observability import (
    audit,
    configure_tracing,
    record_feedback,
    run_config,
)


class PlantAssistant:
    def __init__(self, graph=None):
        self.tracing = configure_tracing()  # LangSmith on/off from .env
        self.graph = graph or build_graph()

    def ask(self, question: str, channel: str = "api", role: str | None = None) -> dict:
        role = rbac.get_role(role or get_settings().default_role).name
        run_id = uuid.uuid4()
        start = time.perf_counter()
        config = run_config(run_id, channel)
        config["tags"].append(f"role:{role}")
        state = self.graph.invoke({"question": question, "role": role}, config=config)
        result = {
            "run_id": str(run_id),  # pass back to feedback()
            "role": role,
            "question": state["question"],
            "answer": state.get("answer", ""),
            "outcome": state.get("outcome", ""),
            "safety_alert": state.get("safety_alert", False),
            "route": state.get("route", {}),
            "searched_sources": [t["source"] for t in state.get("targets", [])],
            "restricted_sources": state.get("restricted_sources", []),
            "citations": state.get("citations", []),
            "contexts": [c["content"] for c in state.get("context", [])],   # for RAGAS
            "grounded": state.get("grounded"),
            "guardrail": state.get("guardrail", {}),
            "trace": state.get("trace", []),
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
        audit(result)
        METRICS.record(result)
        return result

    @staticmethod
    def feedback(run_id: str, score: int, comment: str | None = None) -> dict:
        METRICS.inc("feedback_total", score=str(score))
        return record_feedback(run_id, score, comment)


@lru_cache
def get_assistant() -> PlantAssistant:
    return PlantAssistant()
