"""REST API - how enterprise applications integrate with the Llama-based assistant.

    uvicorn supplykb.api:app --port 8003      ->  http://localhost:8003/docs

Endpoints: POST /ask, POST /summarize, POST /search, GET /documents, GET /images/{image_id},
POST /feedback, GET /roles, GET /health, GET /metrics, GET /metrics/summary.  Auth: X-API-Key -> role.
"""

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from supplykb import rbac
from supplykb.config import get_settings
from supplykb.observability import METRICS, langsmith_enabled


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000, examples=["What must happen if a shipment is above 8 C for 3 hours?"])


class SummarizeRequest(BaseModel):
    doc_id: str = Field(examples=["DEV-2026-014"])
    style: Literal["brief", "detailed", "executive"] = "brief"


class SearchRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500, examples=["temperature excursion"])


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
    from supplykb.ingest import ensure_index
    from supplykb.service import get_assistant

    ensure_index()
    get_assistant()
    yield


app = FastAPI(title="Supply Chain Knowledge Assistant", version="0.1.0", lifespan=lifespan)


def _public(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "contexts"}


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "llm": s.ollama_chat_model, "vision": s.ollama_vision_model, "langsmith_tracing": langsmith_enabled()}


@app.get("/roles")
def roles() -> dict:
    all_roles, _ = rbac.load_roles()
    return {n: {"description": r.description, "clearance": r.clearance, "tasks": list(r.tasks)} for n, r in all_roles.items()}


@app.post("/ask")
async def ask(req: AskRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from supplykb.service import get_assistant

    return _public(await run_in_threadpool(get_assistant().ask, req.question, role.name, "api", "qa"))


@app.post("/summarize")
async def summarize(req: SummarizeRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from supplykb.service import get_assistant

    return _public(await run_in_threadpool(get_assistant().ask, f"Summarize {req.doc_id}", role.name, "api", "summarize",
                                           req.doc_id.upper(), req.style))


@app.post("/search")
async def search(req: SearchRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from supplykb.service import get_assistant

    return _public(await run_in_threadpool(get_assistant().ask, req.query, role.name, "api", "search"))


@app.get("/documents")
def documents(role: rbac.Role = Depends(current_role)) -> list[dict]:
    from supplykb.retrieval import get_retrievers

    seen = {}
    for _, _, meta, _ in get_retrievers()["documents"]._load():
        if role.can_see(meta["classification"]):
            seen.setdefault(meta["doc_id"], {"doc_id": meta["doc_id"], "title": meta["title"], "classification": meta["classification"]})
    return sorted(seen.values(), key=lambda d: d["doc_id"])


@app.get("/images/{image_id}")
def image(image_id: str, role: rbac.Role = Depends(current_role)):
    from supplykb.retrieval import get_retrievers

    for _, _, meta, _ in get_retrievers()["documents"]._load():
        if meta.get("image_id") == image_id:
            if not role.can_see(meta["classification"]):
                raise HTTPException(status_code=403, detail="Not cleared for the source document")
            return FileResponse(get_settings().extracted_dir.parent.parent / meta["image_path"])
    raise HTTPException(status_code=404, detail="Unknown image")


@app.post("/feedback")
async def feedback(req: FeedbackRequest, _: rbac.Role = Depends(current_role)) -> dict:
    from supplykb.service import get_assistant

    return await run_in_threadpool(get_assistant().feedback, req.run_id, req.score, req.comment)


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render()


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    return METRICS.summary()
