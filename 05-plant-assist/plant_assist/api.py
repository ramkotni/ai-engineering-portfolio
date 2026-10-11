"""REST API.  uvicorn plant_assist.api:app --port 8005   ->  http://localhost:8005/docs

Auth: X-API-Key (demo keys in plant_assist/roles.yaml) -> role.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from plant_assist import rbac
from plant_assist.config import get_settings
from plant_assist.metrics import METRICS
from plant_assist.observability import langsmith_enabled


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000, examples=["How do I replace the main cylinder seal on the HP-200 press?"])


class FeedbackRequest(BaseModel):
    run_id: str
    score: int = Field(ge=0, le=1, description="1 = helpful, 0 = not helpful")
    comment: str | None = Field(default=None, max_length=1000)


def current_role(x_api_key: str | None = Header(default=None)) -> rbac.Role:
    role = rbac.role_for_api_key(x_api_key)
    if role is None:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")
    return role


@asynccontextmanager
async def lifespan(_: FastAPI):
    from plant_assist.ingest import ensure_index
    from plant_assist.service import get_assistant

    ensure_index()   # builds the Chroma index on first start (e.g. a fresh container)
    get_assistant()  # compile the graph once
    yield


app = FastAPI(title="PlantAssist", version="0.3.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "llm_provider": s.llm_provider, "embedding_provider": s.embedding_provider,
            "langsmith_tracing": langsmith_enabled()}


@app.get("/roles")
def roles() -> dict:
    all_roles, _ = rbac.load_roles()
    return {n: {"description": r.description, "sources": list(r.sources)} for n, r in all_roles.items()}


@app.post("/ask")
async def ask(req: AskRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from plant_assist.service import get_assistant

    result = await run_in_threadpool(get_assistant().ask, req.question, "api", role.name)
    return {k: v for k, v in result.items() if k != "contexts"}


@app.post("/feedback")
async def feedback(req: FeedbackRequest, _: rbac.Role = Depends(current_role)) -> dict:
    from plant_assist.service import get_assistant

    return await run_in_threadpool(get_assistant().feedback, req.run_id, req.score, req.comment)


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render()


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    return METRICS.summary()
