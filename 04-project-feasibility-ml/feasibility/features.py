"""Feature engineering - implemented as a scikit-learn transformer so training and serving use identical code."""

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin

from feasibility.data import CATEGORICAL, NUMERIC

# (readiness_gap = 9 - TRL was removed: perfectly collinear with tech_readiness, it split one effect into two coefficients)
ENGINEERED = ["log_budget_per_week", "complexity_x_dependencies", "staffing_pressure", "experience_per_complexity"]
FEATURES_NUM = NUMERIC + ENGINEERED
FEATURE_DESCRIPTIONS = {
    "complexity": "project complexity (1-10)",
    "budget_usd": "total budget",
    "timeline_weeks": "planned timeline",
    "tech_readiness": "technology readiness level (TRL 1-9)",
    "resource_availability": "share of required staff secured (0-1)",
    "dependency_count": "number of external dependencies",
    "team_experience_years": "average team experience",
    "stakeholder_count": "number of stakeholder groups",
    "log_budget_per_week": "budget per week (log)",
    "complexity_x_dependencies": "complexity x dependencies",
    "staffing_pressure": "complexity relative to secured staff",
    "experience_per_complexity": "team experience relative to complexity",
}


class FeatureBuilder(BaseEstimator, TransformerMixin):
    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()
        X["log_budget_per_week"] = np.log1p(X.budget_usd / X.timeline_weeks)
        X["complexity_x_dependencies"] = X.complexity * X.dependency_count
        X["staffing_pressure"] = X.complexity / (X.resource_availability + 0.1)
        X["experience_per_complexity"] = X.team_experience_years / X.complexity
        return X[FEATURES_NUM + CATEGORICAL]
