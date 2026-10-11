"""LangSmith observability: tracing, run metadata and feedback.

How it works
- LangChain / LangGraph trace automatically through their callback system when
  LANGSMITH_TRACING=true and LANGSMITH_API_KEY are present in *os.environ*.
  pydantic-settings reads `.env` into Settings but does NOT export it to
  os.environ, so `configure_tracing()` exports the values explicitly.
- Every turn gets a pre-generated `run_id` (the root trace id), a run name,
  tags and metadata. metadata["session_id"] groups the turns of one
  conversation into a LangSmith *thread*.
- Feedback: automatic scores (grounded, guardrail_blocked) are attached to each
  trace, and end users can add a thumbs up/down via POST /feedback.

Privacy: questions are PII-redacted before the graph runs, so traces never
contain raw SSNs or card numbers; the member id is sent only as a hash.
Everything here is a no-op when tracing is disabled.
"""
from __future__ import annotations

import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

from app.config import Settings

logger = logging.getLogger(__name__)
_feedback_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="ls-feedback")


def configure_tracing(settings: Settings) -> bool:
    """Export LangSmith settings to os.environ. Returns True if tracing is on."""
    if not settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "false"
        return False
    if not settings.langsmith_api_key:
        logger.warning("LANGSMITH_TRACING=true but LANGSMITH_API_KEY is missing; tracing disabled")
        os.environ["LANGSMITH_TRACING"] = "false"
        return False
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    if settings.langsmith_endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    os.environ["LANGSMITH_HIDE_INPUTS"] = str(settings.langsmith_hide_inputs).lower()
    os.environ["LANGSMITH_HIDE_OUTPUTS"] = str(settings.langsmith_hide_outputs).lower()
    logger.info("langsmith tracing enabled", extra={"extra_fields": {"project": settings.langsmith_project}})
    return True


def tracing_enabled() -> bool:
    return os.environ.get("LANGSMITH_TRACING", "").lower() == "true" and bool(os.environ.get("LANGSMITH_API_KEY"))


def member_hash(member_id: str | None) -> str | None:
    """Pseudonymous member id for trace metadata (filterable, not reversible)."""
    return hashlib.sha256(member_id.encode()).hexdigest()[:12] if member_id else None


def run_config(settings: Settings, session_id: str, member_id: str | None, run_id: str) -> dict:
    """LangChain RunnableConfig keys that label the root trace of one turn."""
    model = settings.ollama_chat_model if settings.llm_provider == "ollama" else settings.bedrock_chat_model_id
    return {
        "run_id": run_id,
        "run_name": "member_assist_turn",
        "tags": [f"env:{settings.app_env}", f"llm:{settings.llm_provider}", f"critic:{settings.groundedness_mode}"],
        "metadata": {
            "session_id": session_id,  # LangSmith groups traces with the same session_id into a thread
            "member_hash": member_hash(member_id),
            "llm_provider": settings.llm_provider,
            "model": model,
            "vector_backend": settings.vector_backend,
            "groundedness_mode": settings.groundedness_mode,
            "app_version": settings.app_version,
        },
    }


@lru_cache
def _client():
    from langsmith import Client

    return Client()


def automatic_feedback(guardrail: dict, grounded: bool | None, intent: str | None) -> list[tuple[str, float, str | None]]:
    """(key, score, comment) triples derived from the turn's outcome."""
    fb = [("guardrail_blocked", 1.0 if guardrail.get("blocked") else 0.0, guardrail.get("reason"))]
    if grounded is not None:
        fb.append(("grounded", 1.0 if grounded else 0.0, None))
    if "tool_authz_denied" in guardrail.get("flags", []):
        fb.append(("authz_denied", 1.0, "cross-member claim access attempt"))
    if intent:
        fb.append((f"intent:{intent}", 1.0, None))
    return fb


def record_automatic_feedback(run_id: str, guardrail: dict, grounded: bool | None, intent: str | None) -> None:
    if not tracing_enabled():
        return
    for key, score, comment in automatic_feedback(guardrail, grounded, intent):
        _feedback_pool.submit(_safe_feedback, run_id, key, score, comment)


def submit_user_feedback(run_id: str, score: float, comment: str | None = None) -> bool:
    """Thumbs up (1) / down (0) from the UI. Returns False if tracing is disabled."""
    if not tracing_enabled():
        return False
    _feedback_pool.submit(_safe_feedback, run_id, "user_score", score, comment)
    return True


def _safe_feedback(run_id: str, key: str, score: float, comment: str | None) -> None:
    try:
        _client().create_feedback(run_id=run_id, key=key, score=score, comment=comment)
    except Exception as exc:  # observability must never break the product
        logger.warning("langsmith feedback failed: %s", exc)
