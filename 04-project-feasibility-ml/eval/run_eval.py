"""Model evaluation report.   python -m eval.run_eval [--advisor N]

- hold-out metrics + model comparison from the model card
- decision-threshold sweep (precision / recall trade-off for the intake board)
- scoring of the 8 new projects
- advisor numeric-grounding check on N projects (uses the LLM; default 0)
Results -> eval/results/eval_report.json
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from feasibility.config import get_settings
from feasibility.data import training_frame
from feasibility.predict import load_model, predict_batch

HERE = Path(__file__).parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--advisor", type=int, default=0, help="run the LLM advisor on N new projects")
    args = ap.parse_args()
    s = get_settings()
    model, card = load_model()
    X, y, _ = training_frame()
    _, X_test, _, y_test = train_test_split(X.drop(columns="project_id"), y, test_size=s.test_size, stratify=y,
                                            random_state=s.random_state)
    proba = model.predict_proba(X_test)[:, 1]
    sweep = []
    for t in np.arange(0.3, 0.75, 0.05):
        pred = (proba >= t).astype(int)
        sweep.append({"threshold": round(float(t), 2), "precision": round(precision_score(y_test, pred), 3),
                      "recall": round(recall_score(y_test, pred), 3), "f1": round(f1_score(y_test, pred), 3),
                      "approved_share": round(float(pred.mean()), 3)})
    new = predict_batch(pd.read_csv(s.data_dir / "new_projects.csv"))
    report = {
        "model": card["model"], "selection_reason": card["selection_reason"],
        "comparison": {k: v["cv_auc_mean"] for k, v in card["comparison"].items()},
        "test_metrics": {k: v for k, v in card["test_metrics"].items() if k != "calibration"},
        "calibration": card["test_metrics"]["calibration"],
        "threshold_sweep": sweep,
        "new_projects": [{k: r[k] for k in ("project_id", "feasibility_probability", "risk_band")} |
                         {"top_risk": r["top_negative_drivers"][0]["feature"] if r["top_negative_drivers"] else None} for r in new],
        "top_coefficients": card["coefficients"][:6],
    }
    if args.advisor:
        from feasibility.advisor import build_advisor

        advisor, rows = build_advisor(), pd.read_csv(s.data_dir / "new_projects.csv").to_dict("records")[: args.advisor]
        checks = []
        for r in rows:
            st = advisor.invoke({"project": r, "notes": ""})
            checks.append({"project_id": r["project_id"], "unsupported_numbers": st["guardrail"]["unsupported_numbers"],
                           "advice_chars": len(st["advice"])})
        report["advisor"] = {"runs": len(checks), "grounded_rate": round(sum(not c["unsupported_numbers"] for c in checks) / len(checks), 3),
                             "details": checks}
    (HERE / "results").mkdir(exist_ok=True)
    (HERE / "results" / "eval_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in ("model", "comparison", "test_metrics")}, indent=2))
    print(pd.DataFrame(sweep).to_string(index=False))


if __name__ == "__main__":
    main()
