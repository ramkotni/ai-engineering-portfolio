"""REST API.   uvicorn stockbrief.api:app --port 8008   ->   http://localhost:8008/docs

Endpoints: POST /briefing, GET /quote/{ticker}, POST /ask, GET /filings/{ticker}, GET /audit (compliance),
POST /feedback, GET /roles, GET /health, GET /metrics, GET /metrics/summary.   Auth: X-API-Key -> role.
"""

import json
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from stockbrief import rbac
from stockbrief.config import get_settings
from stockbrief.observability import METRICS, langsmith_enabled

Source = Literal["synthetic", "live"]


class BriefingRequest(BaseModel):
    company: str = Field(min_length=1, max_length=120, examples=["NWRB"])
    source: Source = "synthetic"


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000, examples=["What does HLXB say about its cash runway?"])
    source: Source = "synthetic"


class FeedbackRequest(BaseModel):
    run_id: str
    score: int = Field(ge=0, le=1)
    comment: str | None = None


def current_role(x_api_key: str | None = Header(default=None)) -> rbac.Role:
    role = rbac.role_for_api_key(x_api_key)
    if role is None:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")
    return role


@asynccontextmanager
async def lifespan(_: FastAPI):
    from stockbrief.ingest import ensure_index
    from stockbrief.service import get_service

    ensure_index()
    get_service()
    yield


app = FastAPI(title="Stock Briefing Assistant", version="0.1.0", lifespan=lifespan)


def _public(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "contexts"}


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "llm": s.ollama_chat_model, "data_source": s.data_source, "sec_live_configured": bool(s.sec_user_agent.strip()),
            "langsmith_tracing": langsmith_enabled()}


@app.get("/roles")
def roles() -> dict:
    all_roles, _ = rbac.load_roles()
    return {n: {"description": r.description, "tasks": list(r.tasks), "live_data": r.live_data} for n, r in all_roles.items()}


@app.post("/briefing")
async def briefing(req: BriefingRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from stockbrief.service import get_service

    return _public(await run_in_threadpool(get_service().brief, req.company, role.name, req.source, "api"))


@app.get("/quote/{ticker}")
async def quote(ticker: str, source: Source = "synthetic", role: rbac.Role = Depends(current_role)) -> dict:
    from stockbrief.service import get_service

    return _public(await run_in_threadpool(get_service().quote, ticker.upper(), role.name, source, "api"))


@app.post("/ask")
async def ask(req: AskRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from stockbrief.service import get_service

    return _public(await run_in_threadpool(get_service().ask, req.question, role.name, req.source, "api"))


@app.get("/filings/{ticker}")
def filings(ticker: str, _: rbac.Role = Depends(current_role)) -> list[dict]:
    """Filings indexed for a ticker (synthetic, or live ones fetched by an earlier briefing)."""
    from stockbrief.retrieval import get_retrievers

    seen = {}
    for _, _, meta, _ in get_retrievers()["filings"]._load():
        if meta["ticker"] == ticker.upper():
            seen.setdefault(meta["doc_id"], {"form": meta["form"], "filed": meta["filed"], "source": meta["source"], "url": meta["url"],
                                             "sections": set()})["sections"].add(meta["section"])
    return [{**v, "sections": sorted(v["sections"])} for v in sorted(seen.values(), key=lambda v: v["filed"], reverse=True)]


@app.get("/audit")
def audit(limit: int = 50, role: rbac.Role = Depends(current_role)) -> list[dict]:
    """Latest audit records (who asked what, outcome, guardrail flags) - compliance officers only."""
    if not role.allows("audit"):
        raise HTTPException(status_code=403, detail="Audit log is restricted to compliance")
    path = get_settings().audit_log_path
    if not path or not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()[-limit:]]


@app.post("/feedback")
async def feedback(req: FeedbackRequest, _: rbac.Role = Depends(current_role)) -> dict:
    from stockbrief.service import get_service

    return await run_in_threadpool(get_service().feedback, req.run_id, req.score, req.comment)


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render()


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    return METRICS.summary()
