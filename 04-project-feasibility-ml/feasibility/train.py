"""Training: compare algorithms with cross-validation, tune, select for interpretability, evaluate, save.

    python -m feasibility.train

1. Load + validate + clean (data.py)
2. Pipeline = FeatureBuilder -> ColumnTransformer(impute+scale numeric, one-hot categorical) -> model
3. 5-fold stratified CV ROC-AUC for LogisticRegression, RandomForest, GradientBoosting, SVM
4. GridSearchCV over LogisticRegression C / penalty
5. Selection rule: LogisticRegression if its CV AUC is within 0.02 of the best model (interpretability:
   coefficients map directly to feasibility drivers for the business)
6. Hold-out test metrics (ROC-AUC, PR-AUC, accuracy, precision, recall, F1, Brier, confusion matrix,
   calibration), model card and training-distribution stats for drift monitoring -> models/
"""

import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, average_precision_score, brier_score_loss, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC

from feasibility.config import get_settings
from feasibility.data import CATEGORICAL, NUMERIC, training_frame
from feasibility.features import FEATURES_NUM, FeatureBuilder


def make_pipeline(model) -> Pipeline:
    pre = ColumnTransformer([
        ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), FEATURES_NUM),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL),
    ])
    return Pipeline([("features", FeatureBuilder()), ("pre", pre), ("model", model)])


CANDIDATES = {
    "logistic_regression": LogisticRegression(max_iter=2000),
    "random_forest": RandomForestClassifier(n_estimators=300, min_samples_leaf=5, random_state=42, n_jobs=2),
    "gradient_boosting": GradientBoostingClassifier(random_state=42),
    "svm_rbf": SVC(probability=True, random_state=42),
}


def train(save: bool = True) -> dict:
    s = get_settings()
    X, y, report = training_frame()
    X_train, X_test, y_train, y_test = train_test_split(X.drop(columns="project_id"), y, test_size=s.test_size,
                                                        stratify=y, random_state=s.random_state)
    cv = StratifiedKFold(n_splits=s.cv_folds, shuffle=True, random_state=s.random_state)
    comparison = {}
    for name, model in CANDIDATES.items():
        scores = cross_val_score(make_pipeline(model), X_train, y_train, cv=cv, scoring="roc_auc", n_jobs=1)
        comparison[name] = {"cv_auc_mean": round(float(scores.mean()), 4), "cv_auc_std": round(float(scores.std()), 4)}

    grid = GridSearchCV(make_pipeline(LogisticRegression(max_iter=5000, solver="saga")),
                        {"model__C": [0.01, 0.1, 0.3, 1, 3, 10], "model__l1_ratio": [0.0, 0.5, 1.0]},  # L2, elastic net, L1
                        cv=cv, scoring="roc_auc", n_jobs=1)
    grid.fit(X_train, y_train)
    comparison["logistic_regression_tuned"] = {"cv_auc_mean": round(float(grid.best_score_), 4), "best_params": grid.best_params_}

    best_name = max(comparison, key=lambda k: comparison[k]["cv_auc_mean"])
    lr_auc = comparison["logistic_regression_tuned"]["cv_auc_mean"]
    if comparison[best_name]["cv_auc_mean"] - lr_auc <= s.interpretability_tolerance:
        chosen, model = "logistic_regression_tuned", grid.best_estimator_
        reason = ("best cross-validated AUC and the most interpretable model" if best_name.startswith("logistic")
                  else f"within {s.interpretability_tolerance} AUC of the best ({best_name}); chosen for interpretability")
    else:
        chosen = best_name
        model = make_pipeline(CANDIDATES[best_name]).fit(X_train, y_train)
        reason = "best cross-validated AUC"

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= s.decision_threshold).astype(int)
    frac_pos, mean_pred = calibration_curve(y_test, proba, n_bins=5)
    metrics = {
        "roc_auc": round(roc_auc_score(y_test, proba), 4), "pr_auc": round(average_precision_score(y_test, proba), 4),
        "accuracy": round(accuracy_score(y_test, pred), 4), "precision": round(precision_score(y_test, pred), 4),
        "recall": round(recall_score(y_test, pred), 4), "f1": round(f1_score(y_test, pred), 4),
        "brier": round(brier_score_loss(y_test, proba), 4),
        "confusion_matrix": confusion_matrix(y_test, pred).tolist(),
        "calibration": {"mean_predicted": [round(x, 3) for x in mean_pred], "observed_rate": [round(x, 3) for x in frac_pos]},
        "test_rows": len(y_test), "positive_rate": round(float(y_test.mean()), 3),
    }
    card = {
        "model": chosen, "selection_reason": reason, "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "comparison": comparison, "test_metrics": metrics, "data_validation": report.to_dict(),
        "features": FEATURES_NUM + CATEGORICAL, "threshold": s.decision_threshold,
        "coefficients": coefficients(model) if "logistic" in chosen else None,
        "training_stats": {c: training_stats(X_train[c]) for c in NUMERIC},
        "intended_use": "Decision support for project intake reviews. Not an automatic approval mechanism.",
        "limitations": "Trained on synthetic data; inputs outside the training ranges are flagged as out-of-distribution.",
    }
    if save:
        s.model_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, s.model_dir / "feasibility_model.joblib")
        (s.model_dir / "model_card.json").write_text(json.dumps(card, indent=2))
    return card


def training_stats(col: pd.Series) -> dict:
    """Range for out-of-distribution checks + the reference histogram for PSI drift monitoring
    (decile edges, de-duplicated for discrete features, and the training share in each bin)."""
    values = col.dropna().to_numpy(dtype=float)
    edges = np.unique(np.percentile(values, np.arange(0, 101, 10)))
    expected = np.histogram(values, bins=edges)[0] / len(values) if len(edges) > 1 else np.array([1.0])
    return {"mean": float(values.mean()), "std": float(values.std()), "min": float(values.min()), "max": float(values.max()),
            "bins": [float(e) for e in edges], "expected": [round(float(x), 5) for x in expected]}


def coefficients(model: Pipeline) -> list[dict]:
    names = model.named_steps["pre"].get_feature_names_out()
    coefs = model.named_steps["model"].coef_[0]
    rows = [{"feature": n.split("__", 1)[1], "coefficient": round(float(c), 4), "odds_ratio": round(float(np.exp(c)), 3)}
            for n, c in zip(names, coefs)]
    return sorted(rows, key=lambda r: abs(r["coefficient"]), reverse=True)


if __name__ == "__main__":
    c = train()
    print(json.dumps({k: c[k] for k in ("model", "selection_reason", "comparison", "test_metrics")}, indent=2))
    print(pd.DataFrame(c["coefficients"]).head(10).to_string(index=False) if c["coefficients"] else "")
