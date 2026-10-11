"""Data loading, validation and cleaning (pandas / numpy).

Validation produces a report of every problem found; cleaning fixes what can be fixed safely and leaves
missing values for the model pipeline's imputer (so training and serving impute identically).
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from feasibility.config import get_settings

NUMERIC = ["complexity", "budget_usd", "timeline_weeks", "tech_readiness", "resource_availability",
           "dependency_count", "team_experience_years", "stakeholder_count"]
CATEGORICAL = ["project_type", "region"]
TARGET = "feasible"
RANGES = {"complexity": (1, 10), "budget_usd": (10_000, 20_000_000), "timeline_weeks": (2, 260), "tech_readiness": (1, 9),
          "resource_availability": (0, 1), "dependency_count": (0, 50), "team_experience_years": (0, 40),
          "stakeholder_count": (1, 200)}
PROJECT_TYPES = {"application", "infrastructure", "data_platform", "ai_ml", "integration"}
REGIONS = {"americas", "emea", "apj"}


@dataclass
class ValidationReport:
    rows: int
    duplicates: int = 0
    missing: dict = field(default_factory=dict)
    out_of_range: dict = field(default_factory=dict)
    unknown_categories: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.__dict__


def load_raw(name: str = "projects.csv") -> pd.DataFrame:
    return pd.read_csv(get_settings().data_dir / name)


def validate(df: pd.DataFrame) -> ValidationReport:
    r = ValidationReport(rows=len(df), duplicates=int(df.duplicated().sum()))
    r.missing = {c: int(n) for c, n in df[NUMERIC + CATEGORICAL].isna().sum().items() if n}
    for c, (lo, hi) in RANGES.items():
        n = int(((df[c] < lo) | (df[c] > hi)).sum())
        if n:
            r.out_of_range[c] = n
    for c, allowed in (("project_type", PROJECT_TYPES), ("region", REGIONS)):
        bad = sorted(set(df[c].dropna()) - allowed)
        if bad:
            r.unknown_categories[c] = bad
    return r


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Deterministic fixes: drop duplicates, normalise category spelling, repair the known budget unit error,
    null-out impossible values (imputed later)."""
    df = df.drop_duplicates().copy()
    for c in CATEGORICAL:
        df[c] = df[c].str.strip().str.lower()
    # Budgets entered in USD instead of USD-thousands appear 1,000x too large.
    too_big = df.budget_usd > RANGES["budget_usd"][1]
    df.loc[too_big, "budget_usd"] = df.loc[too_big, "budget_usd"] / 1000
    for c, (lo, hi) in RANGES.items():
        df.loc[(df[c] < lo) | (df[c] > hi), c] = np.nan
    return df.reset_index(drop=True)


def training_frame() -> tuple[pd.DataFrame, pd.Series, ValidationReport]:
    raw = load_raw()
    report = validate(raw)
    df = clean(raw)
    return df[["project_id"] + NUMERIC + CATEGORICAL], df[TARGET].astype(int), report
