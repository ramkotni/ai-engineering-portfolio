"""Serving: input validation, prediction, per-feature explanation, out-of-distribution flags."""

import json
from functools import lru_cache
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from feasibility.config import get_settings
from feasibility.data import CATEGORICAL, NUMERIC
from feasibility.features import FEATURE_DESCRIPTIONS


class ProjectInput(BaseModel):
    """Input guardrail #1: types and business ranges are enforced before the model sees anything."""

    project_id: str = Field(default="adhoc", max_length=40)
    project_type: Literal["application", "infrastructure", "data_platform", "ai_ml", "integration"]
    region: Literal["americas", "emea", "apj"]
    complexity: int = Field(ge=1, le=10)
    budget_usd: float = Field(ge=10_000, le=20_000_000)
    timeline_weeks: int = Field(ge=2, le=260)
    tech_readiness: int = Field(ge=1, le=9, description="TRL 1-9")
    resource_availability: float = Field(ge=0, le=1)
    dependency_count: int = Field(ge=0, le=50)
    team_experience_years: float = Field(ge=0, le=40)
    stakeholder_count: int = Field(ge=1, le=200)


@lru_cache
def load_model():
    s = get_settings()
    path = s.model_dir / "feasibility_model.joblib"
    if not path.exists():
        from feasibility.train import train

        train()
    return joblib.load(path), json.loads((s.model_dir / "model_card.json").read_text())


def ood_flags(row: dict, card: dict) -> list[str]:
    """Input guardrail #2: values outside the training range get a warning (the model is extrapolating)."""
    flags = []
    for c in NUMERIC:
        lo, hi = card["training_stats"][c]["min"], card["training_stats"][c]["max"]
        if not lo <= row[c] <= hi:
            flags.append(f"{c}={row[c]} outside training range [{lo:g}, {hi:g}]")
    return flags


def explain(model, frame: pd.DataFrame) -> list[dict]:
    """Contribution of each feature to the log-odds = coefficient x standardised value (logistic regression)."""
    pre, clf = model.named_steps["pre"], model.named_steps["model"]
    if not hasattr(clf, "coef_"):
        return []
    x = pre.transform(model.named_steps["features"].transform(frame))[0]
    names = [n.split("__", 1)[1] for n in pre.get_feature_names_out()]
    contribs = [{"feature": n, "contribution": round(float(c * v), 3),
                 "description": FEATURE_DESCRIPTIONS.get(n, n.replace("_", " "))}
                for n, c, v in zip(names, clf.coef_[0], x) if abs(c * v) > 1e-6]
    return sorted(contribs, key=lambda d: abs(d["contribution"]), reverse=True)


def predict(project: ProjectInput) -> dict:
    model, card = load_model()
    row = project.model_dump()
    frame = pd.DataFrame([{k: row[k] for k in NUMERIC + CATEGORICAL}])
    p = float(model.predict_proba(frame)[0, 1])
    drivers = explain(model, frame)
    return {
        "project_id": project.project_id,
        "feasibility_probability": round(p, 3),
        "prediction": "feasible" if p >= card["threshold"] else "at_risk",
        "risk_band": "low risk" if p >= 0.7 else "medium risk" if p >= 0.4 else "high risk",
        "top_positive_drivers": [d for d in drivers if d["contribution"] > 0][:3],
        "top_negative_drivers": [d for d in drivers if d["contribution"] < 0][:3],
        "ood_warnings": ood_flags(row, card),
        "model": card["model"],
        "budget_per_week_usd": round(row["budget_usd"] / row["timeline_weeks"]),
    }


def predict_batch(frame: pd.DataFrame) -> list[dict]:
    return [predict(ProjectInput(**{k: (v.item() if isinstance(v, np.generic) else v) for k, v in r.items()}))
            for r in frame.to_dict("records")]
