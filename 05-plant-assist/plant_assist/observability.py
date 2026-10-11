"""Monitoring: LangSmith tracing + feedback, and a local JSONL audit log.

LangSmith (optional, set in .env):
    LANGSMITH_TRACING=true
    LANGSMITH_API_KEY=lsv2_...
    LANGSMITH_PROJECT=plant-assist
    LANGSMITH_HIDE_INPUTS=true / LANGSMITH_HIDE_OUTPUTS=true   # keep document text out of LangSmith
When enabled, every graph run is traced automatically (each node, LLM call, retriever, latency,
tokens), tagged with provider/outcome metadata, and supervisor thumbs-up/down is attached to
the run as feedback.

Audit log (always on unless AUDIT_LOG_PATH is empty): one JSON line per question with route,
sources cited, guardrail results, outcome and latency - the plant's own record of what the
assistant told whom, independent of any SaaS.
"""

import json
import logging
import os
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values

from plant_assist.config import PROJECT_ROOT, get_settings

log = logging.getLogger(__name__)
_lock = threading.Lock()


def configure_tracing() -> bool:
    """Export LANGSMITH_*/LANGCHAIN_* keys from .env into the process environment
    (LangChain reads os.environ, not pydantic settings). Returns True if tracing is on."""
    for key, value in dotenv_values(PROJECT_ROOT / ".env").items():
        if key.startswith(("LANGSMITH_", "LANGCHAIN_")) and value is not None:
            os.environ.setdefault(key, value)
    return langsmith_enabled()


def langsmith_enabled() -> bool:
    tracing = (os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2") or "").lower() == "true"
    return tracing and bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))


def run_config(run_id: uuid.UUID, channel: str) -> dict:
    """RunnableConfig for one question: a known run_id (for feedback), name, tags and metadata."""
    s = get_settings()
    model = s.ollama_chat_model if s.llm_provider == "ollama" else s.bedrock_model_id
    return {
        "run_id": run_id,
        "run_name": "plant_assist.ask",
        "tags": ["plant-assist", f"provider:{s.llm_provider}", f"channel:{channel}"],
        "metadata": {"llm_provider": s.llm_provider, "llm_model": model, "embedding_model": s.embedding_model_id,
                     "channel": channel},
    }


def record_feedback(run_id: str, score: int, comment: str | None = None) -> dict:
    """Supervisor rating (1 = helpful, 0 = not helpful) -> LangSmith run feedback + audit log."""
    sent = False
    if langsmith_enabled():
        try:
            from langsmith import Client

            Client().create_feedback(run_id, key="supervisor_rating", score=score, comment=comment)
            sent = True
        except Exception as exc:  # noqa: BLE001 - monitoring must never break the app
            log.warning("LangSmith feedback failed: %s", exc)
    _append({"type": "feedback", "run_id": str(run_id), "score": score, "comment": comment, "langsmith": sent})
    return {"run_id": str(run_id), "recorded": True, "langsmith": sent}


def audit(result: dict) -> None:
    """Append one Q&A record. The question is already PII-redacted by the input guardrail."""
    _append({
        "type": "question",
        "run_id": result.get("run_id"),
        "question": result.get("question"),
        "outcome": result.get("outcome"),
        "route": {k: result.get("route", {}).get(k) for k in ("primary_source", "secondary_sources", "confidence", "method")},
        "searched": result.get("searched_sources"),
        "cited_docs": sorted({c["doc_id"] for c in result.get("citations", [])}),
        "grounded": result.get("grounded"),
        "guardrail": result.get("guardrail"),
        "safety_alert": result.get("safety_alert"),
        "latency_ms": result.get("latency_ms"),
    })


def _append(record: dict) -> None:
    path = get_settings().audit_log_path
    if not path:
        return
    record = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), **record}
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with _lock, open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
    except OSError as exc:
        log.warning("Audit log write failed: %s", exc)
