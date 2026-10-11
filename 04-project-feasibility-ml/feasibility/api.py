"""REST API.   uvicorn feasibility.api:app --port 8004   ->  http://localhost:8004/docs

POST /predict, POST /advise, POST /predict/batch, GET /model, GET /drift, POST /retrain, POST /feedback,
GET /roles, GET /health, GET /metrics, GET /metrics/summary.   Auth: X-API-Key -> role.
"""

import time
import uuid
from functools import lru_cache

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from feasibility import drift
from feasibility.config import get_settings
from feasibility.observability import METRICS, configure_tracing, record_feedback, record_request, run_config
from feasibility.predict import ProjectInput, load_model, predict


@lru_cache
def roles() -> tuple[dict, dict]:
    data = yaml.safe_load(get_settings().roles_file.read_text(encoding="utf-8"))
    return data["roles"], data["demo_api_keys"]


class Caller(BaseModel):
    role: str
    capabilities: list[str]


def caller(x_api_key: str | None = Header(default=None)) -> Caller:
    all_roles, keys = roles()
    name = keys.get(x_api_key or "")
    if not name:
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")
    return Caller(role=name, capabilities=all_roles[name]["capabilities"])


def require(cap: str):
    def check(c: Caller = Depends(caller)) -> Caller:
        if cap not in c.capabilities:
            raise HTTPException(status_code=403, detail=f"Role {c.role} lacks capability '{cap}'")
        return c
    return check


class AdviseRequest(BaseModel):
    project: ProjectInput
    notes: str = Field(default="", max_length=1000, description="free-text context for the advisor")


class FeedbackRequest(BaseModel):
    run_id: str
    score: int = Field(ge=0, le=1)
    comment: str | None = None


app = FastAPI(title="Project Feasibility Prediction", version="0.1.0")
configure_tracing()


@app.get("/health")
def health() -> dict:
    _, card = load_model()
    return {"status": "ok", "model": card["model"], "test_roc_auc": card["test_metrics"]["roc_auc"]}


@app.get("/roles")
def list_roles() -> dict:
    return roles()[0]


@app.post("/predict")
def predict_endpoint(project: ProjectInput, c: Caller = Depends(require("predict"))) -> dict:
    t = time.perf_counter()
    r = predict(project)
    drift.record(project.model_dump())
    if c.role == "stakeholder_viewer":   # score only, no model internals
        r = {k: r[k] for k in ("project_id", "feasibility_probability", "prediction", "risk_band")}
    record_request("predict", c.role, time.perf_counter() - t, r)
    return r


@app.post("/predict/batch")
def batch(projects: list[ProjectInput], c: Caller = Depends(require("batch"))) -> dict:
    t = time.perf_counter()
    results = [predict(p) for p in projects[:500]]
    for p in projects[:500]:
        drift.record(p.model_dump())
    record_request("batch", c.role, time.perf_counter() - t)
    bands = {b: sum(r["risk_band"] == b for r in results) for b in ("low risk", "medium risk", "high risk")}
    return {"count": len(results), "by_risk_band": bands, "results": sorted(results, key=lambda r: r["feasibility_probability"])}


@app.post("/advise")
async def advise(req: AdviseRequest, c: Caller = Depends(require("advise"))) -> dict:
    from feasibility.advisor import build_advisor

    t = time.perf_counter()
    run_id = uuid.uuid4()
    state = await run_in_threadpool(build_advisor().invoke, {"project": req.project.model_dump(), "notes": req.notes},
                                    run_config(run_id, c.role, "api"))
    out = {"run_id": str(run_id), "prediction": state.get("prediction"), "advice": state.get("advice"),
           "playbook_sections": [p.splitlines()[0].lstrip("# ") for p in state.get("playbook", [])],
           "guardrail": state.get("guardrail"), "trace": state.get("trace")}
    record_request("advise", c.role, time.perf_counter() - t, {**(state.get("prediction") or {}), "run_id": str(run_id),
                                                                  "guardrail": state.get("guardrail")})
    return out


@app.get("/model")
def model_card(_: Caller = Depends(require("model"))) -> dict:
    return load_model()[1]


@app.get("/drift")
def drift_endpoint(_: Caller = Depends(require("drift"))) -> dict:
    return drift.drift_report(load_model()[1])


@app.post("/retrain")
def retrain(_: Caller = Depends(require("retrain"))) -> dict:
    from feasibility.train import train

    card = train()
    load_model.cache_clear()
    return {k: card[k] for k in ("model", "selection_reason", "test_metrics")}


@app.post("/feedback")
def feedback(req: FeedbackRequest, _: Caller = Depends(caller)) -> dict:
    return record_feedback(req.run_id, req.score, req.comment)


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return METRICS.render()


@app.get("/metrics/summary")
def metrics_summary() -> dict:
    return METRICS.summary()
