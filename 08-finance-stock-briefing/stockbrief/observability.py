"""Monitoring: LangSmith tracing + feedback, Prometheus-style metrics, JSONL audit log.

LangSmith (optional, in .env): LANGSMITH_TRACING=true, LANGSMITH_API_KEY, LANGSMITH_PROJECT,
LANGSMITH_HIDE_INPUTS / LANGSMITH_HIDE_OUTPUTS for sensitive data.
Metrics: GET /metrics (Prometheus text format) and GET /metrics/summary (JSON).
"""

import json
import logging
import os
import threading
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values

from stockbrief.config import PROJECT_ROOT, get_settings

log = logging.getLogger(__name__)
_lock = threading.Lock()
SERVICE = "stockbrief"
LATENCY_BUCKETS = (0.5, 1, 2.5, 5, 10, 30, 60, 120, 300)


def configure_tracing() -> bool:
    for key, value in dotenv_values(PROJECT_ROOT / ".env").items():
        if key.startswith(("LANGSMITH_", "LANGCHAIN_")) and value is not None:
            os.environ.setdefault(key, value)
    return langsmith_enabled()


def langsmith_enabled() -> bool:
    on = (os.getenv("LANGSMITH_TRACING") or os.getenv("LANGCHAIN_TRACING_V2") or "").lower() == "true"
    return on and bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))


def run_config(run_id: uuid.UUID, role: str, channel: str) -> dict:
    s = get_settings()
    return {"run_id": run_id, "run_name": f"{SERVICE}.ask",
            "tags": [SERVICE, f"role:{role}", f"channel:{channel}", f"provider:{s.llm_provider}"],
            "metadata": {"role": role, "channel": channel, "llm_provider": s.llm_provider,
                         "llm_model": s.ollama_chat_model if s.llm_provider == "ollama" else s.bedrock_model_id}}


# ---------------------------------------------------------------- metrics
class Metrics:
    """Tiny in-process registry rendered in Prometheus text format (no extra dependency)."""

    def __init__(self):
        self.counters: dict[tuple, float] = defaultdict(float)
        self.hist: dict[tuple, list[float]] = defaultdict(list)

    def inc(self, name: str, **labels) -> None:
        with _lock:
            self.counters[(name, tuple(sorted(labels.items())))] += 1

    def observe(self, name: str, value: float, **labels) -> None:
        with _lock:
            self.hist[(name, tuple(sorted(labels.items())))].append(value)

    def render(self) -> str:
        lines = []
        with _lock:
            for (name, labels), v in sorted(self.counters.items()):
                lines.append(f"{SERVICE}_{name}{_fmt(labels)} {v:g}")
            for (name, labels), values in sorted(self.hist.items()):
                for b in LATENCY_BUCKETS:
                    lines.append(f"{SERVICE}_{name}_bucket{_fmt(labels + (('le', str(b)),))} {sum(x <= b for x in values)}")
                lines.append(f"{SERVICE}_{name}_bucket{_fmt(labels + (('le', '+Inf'),))} {len(values)}")
                lines.append(f"{SERVICE}_{name}_sum{_fmt(labels)} {sum(values):.3f}")
                lines.append(f"{SERVICE}_{name}_count{_fmt(labels)} {len(values)}")
        return "\n".join(lines) + "\n"

    def summary(self) -> dict:
        with _lock:
            counts: dict[str, dict] = defaultdict(dict)
            for (name, labels), v in self.counters.items():
                counts[name][",".join(f"{k}={val}" for k, val in labels) or "total"] = v
            lat = [x for values in self.hist.values() for x in values]
        lat.sort()
        return {"counters": counts, "requests": len(lat),
                "latency_p50_s": lat[len(lat) // 2] if lat else None,
                "latency_p95_s": lat[min(len(lat) - 1, int(len(lat) * 0.95))] if lat else None}


def _fmt(labels: tuple) -> str:
    return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""


METRICS = Metrics()


def record_request(result: dict) -> None:
    METRICS.inc("requests_total", intent=result.get("intent", {}).get("intent", "none"),
                role=result["role"], outcome=result["outcome"])
    METRICS.observe("request_latency_seconds", result["latency_ms"] / 1000, outcome=result["outcome"])
    cat = (result.get("guardrail") or {}).get("input_category")
    if cat:
        METRICS.inc("guardrail_blocks_total", category=cat)
    if (result.get("guardrail") or {}).get("output_issues"):
        METRICS.inc("output_guardrail_flags_total")
    if str(result.get("intent", {}).get("method", "")).startswith("keyword"):
        METRICS.inc("intent_fallback_total")
    _append({"type": "question", **{k: result.get(k) for k in
             ("run_id", "role", "question", "outcome", "intent", "plan", "citations", "guardrail", "latency_ms")}})


def record_feedback(run_id: str, score: int, comment: str | None = None) -> dict:
    sent = False
    if langsmith_enabled():
        try:
            from langsmith import Client

            Client().create_feedback(run_id, key="user_rating", score=score, comment=comment)
            sent = True
        except Exception as exc:  # noqa: BLE001 - monitoring must never break the app
            log.warning("LangSmith feedback failed: %s", exc)
    METRICS.inc("feedback_total", score=str(score))
    _append({"type": "feedback", "run_id": run_id, "score": score, "comment": comment, "langsmith": sent})
    return {"run_id": run_id, "recorded": True, "langsmith": sent}


def _append(record: dict) -> None:
    path = get_settings().audit_log_path
    if not path:
        return
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with _lock, open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": datetime.now(UTC).isoformat(timespec="seconds"), **record}, default=str) + "\n")
    except OSError as exc:
        log.warning("Audit log write failed: %s", exc)
