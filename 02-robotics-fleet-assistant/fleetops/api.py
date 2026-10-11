"""REST API.

    uvicorn fleetops.api:app --port 8002     ->  http://localhost:8002/docs

Auth: send X-API-Key (demo keys in fleetops/roles.yaml) - the key decides the role.
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from fleetops import rbac
from fleetops.config import get_settings
from fleetops.observability import METRICS, langsmith_enabled


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000, examples=["Why does R-1007 keep returning to the charger?"])


class FeedbackRequest(BaseModel):
    run_id: str
    score: int = Field(ge=0, le=1)
    comment: str | None = Field(default=None, max_length=1000)


def current_role(x_api_key: str | None = Header(default=None)) -> rbac.Role:
    role = rbac.role_for_api_key(x_api_key)
    if role is None:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")
    return role


@asynccontextmanager
async def lifespan(_: FastAPI):
    from fleetops.ingest import ensure_index
    from fleetops.service import get_assistant

    ensure_index()
    get_assistant()
    yield


app = FastAPI(title="Robotics Fleet Assistant", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health() -> dict:
    s = get_settings()
    return {"status": "ok", "llm_provider": s.llm_provider, "langsmith_tracing": langsmith_enabled()}


@app.get("/roles")
def roles() -> dict:
    all_roles, _ = rbac.load_roles()
    return {name: {"description": r.description, "intents": list(r.intents), "zones": list(r.zones) or "all"}
            for name, r in all_roles.items()}


@app.post("/ask")
async def ask(req: AskRequest, role: rbac.Role = Depends(current_role)) -> dict:
    from fleetops.service import get_assistant

    result = await run_in_threadpool(get_assistant().ask, req.question, role.name, "api")
    return {k: v for k, v in result.items() if k != "contexts"}


@app.post("/feedback")
async def feedback(req: FeedbackRequest, _: rbac.Role = Depends(current_role)) -> dict:
    from fleetops.service import get_assistant

    return await run_in_threadpool(get_assistant().feedback, req.run_id, req.score, req.comment)


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render()


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    return METRICS.summary()
