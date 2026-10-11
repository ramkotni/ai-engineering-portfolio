"""In-process metrics rendered in Prometheus text format (GET /metrics) and as JSON (GET /metrics/summary)."""

import threading
from collections import defaultdict

SERVICE = "plant_assist"
BUCKETS = (0.5, 1, 2.5, 5, 10, 30, 60, 120, 300)
_lock = threading.Lock()


class Metrics:
    def __init__(self):
        self.counters: dict[tuple, float] = defaultdict(float)
        self.latency: list[tuple[str, float]] = []

    def inc(self, name: str, **labels) -> None:
        with _lock:
            self.counters[(name, tuple(sorted(labels.items())))] += 1

    def record(self, result: dict) -> None:
        primary = result.get("route", {}).get("primary_source") or "none"
        self.inc("requests_total", primary_source=primary, role=result["role"], outcome=result["outcome"])
        if result["guardrail"].get("input_category"):
            self.inc("guardrail_blocks_total", category=result["guardrail"]["input_category"])
        if result["guardrail"].get("output_issues"):
            self.inc("output_guardrail_flags_total")
        if result.get("route", {}).get("method") == "keyword-fallback":
            self.inc("router_fallback_total")
        if result.get("restricted_sources"):
            self.inc("role_restricted_total", role=result["role"])
        if result.get("safety_alert"):
            self.inc("safety_alerts_total")
        with _lock:
            self.latency.append((result["outcome"], result["latency_ms"] / 1000))

    def render(self) -> str:
        with _lock:
            lines = [f"{SERVICE}_{n}{_fmt(lbl)} {v:g}" for (n, lbl), v in sorted(self.counters.items())]
            values = [v for _, v in self.latency]
        for b in BUCKETS:
            lines.append(f'{SERVICE}_request_latency_seconds_bucket{{le="{b}"}} {sum(v <= b for v in values)}')
        lines += [f'{SERVICE}_request_latency_seconds_bucket{{le="+Inf"}} {len(values)}',
                  f"{SERVICE}_request_latency_seconds_sum {sum(values):.3f}", f"{SERVICE}_request_latency_seconds_count {len(values)}"]
        return "\n".join(lines) + "\n"

    def summary(self) -> dict:
        with _lock:
            values = sorted(v for _, v in self.latency)
            counts = {f"{n}{dict(lbl) or ''}": v for (n, lbl), v in self.counters.items()}
        return {"requests": len(values), "counters": counts,
                "latency_p50_s": values[len(values) // 2] if values else None,
                "latency_p95_s": values[min(len(values) - 1, int(len(values) * 0.95))] if values else None}


def _fmt(labels: tuple) -> str:
    return "{" + ",".join(f'{k}="{v}"' for k, v in labels) + "}" if labels else ""


METRICS = Metrics()
