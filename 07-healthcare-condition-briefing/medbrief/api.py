"""REST API.   uvicorn medbrief.api:app --port 8007   ->   http://localhost:8007/docs

Endpoints: POST /briefing, POST /ask, GET /conditions, GET /documents, GET /extraction, GET /images/{image_id},
POST /feedback, GET /roles, GET /health, GET /metrics, GET /metrics/summary.   Auth: X-API-Key -> role.
"""

import json
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from medbrief import rbac
from medbrief.conditions import CATALOGUE
from medbrief.config import PROJECT_ROOT, get_settings
from medbrief.observability import METRICS, langsmith_enabled


class BriefingRequest(BaseModel):
    condition: str = Field(min_length=2, max_length=200, examples=["heart failure with reduced ejection fraction"])
    source: Literal["synthetic", "live"] = "synthetic"


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000, examples=["Which drug classes form the four pillars of HFrEF therapy?"])


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
    from medbrief.ingest import ensure_index
    from medbrief.service import get_service

    ensure_index()
    get_service()
    yield


app = FastAPI(title="Condition Briefing Assistant", version="0.1.0", lifespan=lifespan)


def _public(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "contexts"}


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "llm": s.ollama_chat_model, "vision": s.ollama_vision_model, "trials_source": s.trials_source,
            "langsmith_tracing": langsmith_enabled()}


@app.get("/roles")
def roles() -> dict:
    all_roles, _ = rbac.load_roles()
    return {n: {"description": r.description, "clearance": r.clearance, "tasks": list(r.tasks), "live_data": r.live_data}
            for n, r in all_roles.items()}


@app.get("/conditions")
def conditions() -> list[dict]:
    return [{"key": c.key, "name": c.name, "synonyms": list(c.synonyms), "guideline_docs": list(c.guideline_docs)} for c in CATALOGUE.values()]


@app.post("/briefing")
async def briefing(req: BriefingRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from medbrief.service import get_service

    return _public(await run_in_threadpool(get_service().brief, req.condition, role.name, req.source, "api"))


@app.post("/ask")
async def ask(req: AskRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from medbrief.service import get_service

    return _public(await run_in_threadpool(get_service().ask, req.question, role.name, "api"))


@app.get("/documents")
def documents(role: rbac.Role = Depends(current_role)) -> list[dict]:
    from medbrief.retrieval import get_retrievers

    seen = {}
    for _, _, meta, _ in get_retrievers()["documents"]._load():
        if role.can_see(meta["classification"]):
            seen.setdefault(meta["doc_id"], {"doc_id": meta["doc_id"], "title": meta["title"], "classification": meta["classification"]})
    return sorted(seen.values(), key=lambda d: d["doc_id"])


@app.get("/extraction")
def extraction(role: rbac.Role = Depends(current_role)) -> dict:
    """What the extractor did per document (headers removed, columns, merged tables, images, footnotes)."""
    report = json.loads((get_settings().extracted_dir / "extraction_report.json").read_text(encoding="utf-8"))
    return {d: r for d, r in report.items() if role.can_see(r["classification"])}


@app.get("/images/{image_id}")
def image(image_id: str, role: rbac.Role = Depends(current_role)):
    from medbrief.retrieval import get_retrievers

    for _, _, meta, _ in get_retrievers()["documents"]._load():
        if meta.get("image_id") == image_id:
            if not role.can_see(meta["classification"]):
                raise HTTPException(status_code=403, detail="Not cleared for the source document")
            return FileResponse(PROJECT_ROOT / meta["image_path"])
    raise HTTPException(status_code=404, detail="Unknown image")


@app.post("/feedback")
async def feedback(req: FeedbackRequest, _: rbac.Role = Depends(current_role)) -> dict:
    from medbrief.service import get_service

    return await run_in_threadpool(get_service().feedback, req.run_id, req.score, req.comment)


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render()


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    return METRICS.summary()
