"""FastAPI application.

Endpoints
  GET  /            demo chat UI
  GET  /health      readiness + config summary
  POST /chat        primary JSON API
  GET  /ping        Bedrock AgentCore Runtime health contract
  POST /invocations Bedrock AgentCore Runtime invocation contract

The same container image therefore runs on AgentCore Runtime, ECS Fargate,
App Runner or locally with docker compose.
"""
from __future__ import annotations

import hmac
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.config import get_settings
from app.logging_config import setup_logging
from app.observability import submit_user_feedback, tracing_enabled
from app.service import AgentService, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)
STATIC = Path(__file__).parent / "static"
AGENTCORE_SESSION_HEADER = "x-amzn-bedrock-agentcore-runtime-session-id"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings.log_level)
    if getattr(app.state, "service", None) is None:  # tests may inject a service
        app.state.service = AgentService.from_settings(settings)
    logger.info("service ready", extra={"extra_fields": {"llm": settings.llm_provider, "vector": settings.vector_backend}})
    yield


app = FastAPI(title="Evergreen Member Assist - Agentic RAG", version="1.0.0", lifespan=lifespan)


def get_service(request: Request) -> AgentService:
    return request.app.state.service


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = get_settings().api_key
    if expected and not (x_api_key and hmac.compare_digest(x_api_key, expected)):
        raise HTTPException(status_code=401, detail="invalid or missing x-api-key")


@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health(service: AgentService = Depends(get_service)):
    s = service.settings
    return {
        "status": "ok",
        "env": s.app_env,
        "llm_provider": s.llm_provider,
        "embeddings_provider": s.effective_embeddings_provider,
        "vector_backend": s.vector_backend,
        "kb_chunks": service.deps.kb.count(),
        "bedrock_guardrail": bool(s.bedrock_guardrail_id),
        "langsmith_tracing": tracing_enabled(),
        "langsmith_project": s.langsmith_project if tracing_enabled() else None,
    }


class FeedbackRequest(BaseModel):
    run_id: str
    score: float = Field(..., ge=0, le=1, description="1 = thumbs up, 0 = thumbs down")
    comment: str | None = Field(default=None, max_length=1000)


@app.post("/feedback", status_code=202, dependencies=[Depends(require_api_key)])
def feedback(req: FeedbackRequest):
    """End-user feedback, attached to the turn's LangSmith trace (key: user_score)."""
    if not submit_user_feedback(req.run_id, req.score, req.comment):
        raise HTTPException(status_code=503, detail="LangSmith tracing is not enabled")
    return {"status": "accepted"}


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_api_key)])
async def chat(req: ChatRequest, service: AgentService = Depends(get_service)):
    try:
        return await run_in_threadpool(service.ask, req)
    except Exception as exc:
        logger.exception("chat failed")
        raise HTTPException(status_code=502, detail="The assistant is temporarily unavailable.") from exc


# ---------------- Amazon Bedrock AgentCore Runtime HTTP contract ----------
@app.get("/ping")
def ping():
    return {"status": "Healthy"}


@app.post("/invocations")
async def invocations(request: Request, service: AgentService = Depends(get_service)):
    payload = await request.json()
    question = payload.get("prompt") or payload.get("question") or ""
    session_id = request.headers.get(AGENTCORE_SESSION_HEADER) or payload.get("session_id")
    req = ChatRequest(question=question, session_id=session_id, member_id=payload.get("member_id"))
    resp = await run_in_threadpool(service.ask, req)
    return resp.model_dump()


def run() -> None:
    import uvicorn

    uvicorn.run("app.api:app", host="0.0.0.0", port=get_settings().port)


if __name__ == "__main__":
    run()
