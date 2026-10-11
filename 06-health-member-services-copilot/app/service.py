"""Application service: the single entry point used by the API, AgentCore
entrypoint, CLI and evaluation harness."""
from __future__ import annotations

import logging
import time
import uuid

from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.graph.builder import build_graph, make_checkpointer
from app.graph.nodes import Deps
from app.graph.state import initial_turn_state
from app.guardrails import Guardrails
from app.logging_config import log_event
from app.observability import configure_tracing, record_automatic_feedback, run_config
from app.tools import ClaimsRepository
from app.vectorstore import KnowledgeBase

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=8000)
    session_id: str | None = None
    member_id: str | None = Field(default=None, description="From the auth token in production")


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    intent: str | None = None
    citations: list[dict] = []
    grounded: bool | None = None
    guardrail: dict = {}
    trace: list[str] = []
    retrieved: list[dict] = []
    latency_ms: int = 0
    run_id: str | None = None  # LangSmith root trace id; send it back to POST /feedback


class AgentService:
    def __init__(self, settings: Settings, deps: Deps, checkpointer=None):
        self.settings = settings
        self.deps = deps
        self.graph = build_graph(deps, checkpointer or make_checkpointer(settings))

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> AgentService:
        from app.providers import get_chat_model
        from app.vectorstore import get_knowledge_base

        s = settings or get_settings()
        configure_tracing(s)  # must run before the first LangChain call
        kb: KnowledgeBase = get_knowledge_base(s)
        if s.vector_backend == "chroma" and s.auto_ingest and kb.count() == 0:
            from app.ingest import ingest

            logger.info("empty collection, running ingestion on startup")
            ingest(s)
        deps = Deps(
            llm=get_chat_model(s),
            kb=kb,
            claims=ClaimsRepository(s.claims_file),
            guardrails=Guardrails(s),
            settings=s,
        )
        return cls(s, deps)

    def ask(self, req: ChatRequest) -> ChatResponse:
        started = time.perf_counter()
        session_id = req.session_id or str(uuid.uuid4())

        # Edge guardrail: PII is redacted *before* it reaches logs, memory or the LLM.
        sanitized = self.deps.guardrails.sanitize(req.question)
        state_in = initial_turn_state(sanitized.text, req.member_id, sanitized.flags)
        run_id = str(uuid.uuid4())
        config = {
            "configurable": {"thread_id": session_id},
            "recursion_limit": 25,
            **run_config(self.settings, session_id, req.member_id, run_id),  # LangSmith trace labels
        }

        result = self.graph.invoke(state_in, config=config)

        latency_ms = int((time.perf_counter() - started) * 1000)
        resp = ChatResponse(
            answer=result.get("answer", ""),
            session_id=session_id,
            intent=result.get("intent"),
            citations=result.get("citations", []),
            grounded=result.get("grounded"),
            guardrail=result.get("guardrail", {}),
            trace=result.get("trace", []),
            retrieved=[{k: d[k] for k in ("source", "section", "score")} for d in result.get("documents", [])],
            latency_ms=latency_ms,
            run_id=run_id,
        )
        if self.settings.langsmith_auto_feedback:
            record_automatic_feedback(run_id, resp.guardrail, resp.grounded, resp.intent)
        log_event(
            logger, "chat_turn",
            session_id=session_id, member_id=req.member_id, question=sanitized.text, intent=resp.intent,
            grounded=resp.grounded, guardrail=resp.guardrail, trace=resp.trace, latency_ms=latency_ms, run_id=run_id,
        )
        return resp
