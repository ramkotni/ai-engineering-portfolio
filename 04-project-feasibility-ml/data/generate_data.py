"""Synthetic project portfolio for the feasibility model.

    python data/generate_data.py

data/raw/projects.csv - 1,200 historical projects with a known (hidden) logistic ground truth plus realistic
data problems for the cleaning step: ~4% missing values, budget entry typos (x1000), out-of-range TRL codes,
duplicate rows and inconsistent category spelling. data/raw/new_projects.csv - 8 unlabelled projects to score.
data/raw/delivery_playbook.md - mitigation guidance the advisor agent retrieves.
"""

import random
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).parent / "raw"
rng = np.random.default_rng(2024)
random.seed(2024)
TYPES = ["application", "infrastructure", "data_platform", "ai_ml", "integration"]
REGIONS = ["americas", "emea", "apj"]


def make(n: int) -> pd.DataFrame:
    df = pd.DataFrame({
        "project_id": [f"PRJ-{5001 + i}" for i in range(n)],
        "project_type": rng.choice(TYPES, n, p=[0.3, 0.2, 0.2, 0.15, 0.15]),
        "region": rng.choice(REGIONS, n),
        "complexity": rng.integers(1, 11, n),
        "budget_usd": np.round(np.exp(rng.normal(13.0, 0.8, n)), -3),
        "timeline_weeks": rng.integers(6, 105, n),
        "tech_readiness": rng.integers(1, 10, n),          # TRL 1-9
        "resource_availability": np.round(rng.beta(4, 2.5, n), 2),
        "dependency_count": rng.poisson(4, n),
        "team_experience_years": np.round(rng.gamma(4, 1.6, n), 1),
        "stakeholder_count": rng.integers(2, 26, n),
    })
    budget_per_week = df.budget_usd / df.timeline_weeks
    logit = (-1.8 + 0.42 * df.tech_readiness - 0.48 * df.complexity + 3.2 * df.resource_availability
             - 0.22 * df.dependency_count + 0.16 * df.team_experience_years + 0.55 * np.log(budget_per_week / 5000)
             - 0.04 * df.stakeholder_count + df.project_type.map({"ai_ml": -0.6, "integration": -0.3}).fillna(0))
    p = 1 / (1 + np.exp(-logit))
    df["feasible"] = (rng.random(n) < p).astype(int)
    return df


def dirty(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in ("team_experience_years", "resource_availability", "dependency_count", "budget_usd"):
        df.loc[df.sample(frac=0.04, random_state=len(col)).index, col] = np.nan
    typos = df.sample(8, random_state=1).index
    df.loc[typos, "budget_usd"] *= 1000                       # entered in USD instead of USD thousands
    df.loc[df.sample(6, random_state=2).index, "tech_readiness"] = 0   # invalid TRL code
    df.loc[df.sample(25, random_state=3).index, "project_type"] = df.project_type.str.upper()  # spelling drift
    return pd.concat([df, df.sample(12, random_state=4)], ignore_index=True)  # duplicate rows


PLAYBOOK = """# Project Delivery Playbook

Document ID: PMO-PLAY-002 | Owner: Portfolio Management Office

## Low Technology Readiness
- Projects below TRL 6 should run a 4-8 week proof of concept before full funding.
- Fund in stage gates: release the next tranche only after the readiness milestone is met.

## High Complexity
- Split scope into increments of at most 12 weeks with a working release at each increment.
- Assign a solution architect for complexity 8 and above.

## Resource Constraints
- Resource availability below 0.5 is the strongest single predictor of failure: secure named staff before approval.
- Avoid more than 3 concurrent projects per key engineer.

## Many Dependencies
- Above 6 dependencies, create a dependency map and agree interface owners in week 1.
- Track external dependencies weekly in the steering meeting.

## Thin Budget or Timeline
- If budget per week is low, reduce scope or extend the timeline rather than compress testing.
- Hold a 10-15% contingency for projects with complexity 7 and above.

## Inexperienced Team
- Pair teams with under 3 years average experience with an experienced delivery lead.

## Large Stakeholder Groups
- Above 15 stakeholders, appoint a single accountable product owner and a RACI.
"""


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    hist = dirty(make(1200))
    hist.to_csv(RAW / "projects.csv", index=False)
    new = make(8).drop(columns="feasible")
    new["project_id"] = [f"PRJ-NEW-{i + 1}" for i in range(8)]
    new.to_csv(RAW / "new_projects.csv", index=False)
    (RAW / "delivery_playbook.md").write_text(PLAYBOOK, encoding="utf-8")
    print(f"Wrote {len(hist)} historical rows (feasible rate {hist.feasible.mean():.2f}), 8 new projects, playbook -> {RAW}")


if __name__ == "__main__":
    main()
