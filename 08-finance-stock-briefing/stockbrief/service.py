"""Single entry point used by the API, CLI, UI and evaluation."""

import hashlib
import json
import time
import uuid
from functools import lru_cache

from stockbrief import rbac
from stockbrief.config import PROJECT_ROOT, get_settings
from stockbrief.graph import build_graph
from stockbrief.observability import configure_tracing, record_feedback, record_request, run_config


def cache_scope(role: rbac.Role) -> list:
    """Role attributes that change a briefing: style changes the wording; live-data permission changes the sources."""
    return [role.style, role.live_data]


class BriefingService:
    def __init__(self, graph=None, cache: "BriefingCache | None" = None):
        self.tracing = configure_tracing()
        self.graph = graph or build_graph()
        self.cache = cache

    def brief(self, company: str, role: str, source: str | None = None, channel: str = "api") -> dict:
        return self._run(company, role, "briefing", source, channel)

    def quote(self, company: str, role: str, source: str | None = None, channel: str = "api") -> dict:
        return self._run(company, role, "quote", source, channel)

    def ask(self, question: str, role: str, source: str | None = None, channel: str = "api") -> dict:
        return self._run(question, role, "qa", source, channel)

    def _run(self, request: str, role: str, task: str, source: str | None, channel: str) -> dict:
        role_obj = rbac.get_role(role)  # raises KeyError for unknown roles
        source = source or get_settings().data_source
        key = self.cache.key(request, role_obj, source) if task == "briefing" and self.cache and role_obj.allows(task) else None
        hit = self.cache.get(key) if key else None
        if hit:
            start = time.perf_counter()
            result = {**hit, "run_id": str(uuid.uuid4()), "cached": {"from_run": hit["run_id"], "created": hit.get("created")},
                      "trace": ["cache: hit (briefing reused, no LLM call)"] + hit["trace"]}
            result["latency_ms"] = int((time.perf_counter() - start) * 1000)
            record_request(result)
            return result
        run_id = uuid.uuid4()
        start = time.perf_counter()
        state = self.graph.invoke({"request": request, "role": role, "task": task, "source": source},
                                  config=run_config(run_id, role, channel))
        result = {
            "run_id": str(run_id),
            "role": role,
            "task": task,
            "question": state["request"],
            "company": state.get("company") or None,
            "outcome": state.get("outcome", ""),
            "answer": state.get("answer", ""),
            "briefing": state.get("briefing") if state.get("outcome") == "answered" and task != "qa" else None,
            "intent": {"intent": task, "method": "rules"},
            "citations": state.get("citations", []),
            "guardrail": state.get("guardrail", {}),
            "contexts": [e["content"] for e in (state.get("evidence") or state.get("context") or [])],
            "trace": state.get("trace", []),
            "latency_ms": int((time.perf_counter() - start) * 1000),
        }
        record_request(result)
        if key and result["outcome"] == "answered":
            self.cache.put(key, {**result, "created": time.strftime("%Y-%m-%dT%H:%M:%S")})
        return result

    @staticmethod
    def feedback(run_id: str, score: int, comment: str | None = None) -> dict:
        return record_feedback(run_id, score, comment)


class BriefingCache:
    """Disk cache for finished briefings. The key includes everything that changes the content a role may see:
    request, clearance / style, effective data source, index fingerprint, source-data timestamp and prompt version -
    so a role can never receive a briefing built from documents it is not cleared for."""

    def __init__(self, hours: float):
        s = get_settings()
        self.hours = hours
        self.dir = PROJECT_ROOT / ".cache" / "briefings"
        self.data_stamp = max((p.stat().st_mtime for p in s.data_dir.rglob("*") if p.is_file()), default=0)

    def key(self, request: str, role: rbac.Role, source: str) -> str:
        effective = source if source != "live" or role.live_data else "synthetic"
        raw = json.dumps({"q": " ".join(request.lower().split()), "scope": cache_scope(role), "source": effective,
                          "index": get_settings().index_fingerprint, "data": self.data_stamp, "prompt": "briefing/v1"}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:24]

    def get(self, key: str) -> dict | None:
        path = self.dir / f"{key}.json"
        if self.hours <= 0 or not path.exists() or time.time() - path.stat().st_mtime > self.hours * 3600:
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, key: str, result: dict) -> None:
        if self.hours <= 0:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{key}.json").write_text(json.dumps(result, default=str), encoding="utf-8")


@lru_cache
def get_service() -> BriefingService:
    return BriefingService(cache=BriefingCache(get_settings().briefing_cache_hours))
