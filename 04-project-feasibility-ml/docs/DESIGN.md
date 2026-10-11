# Project Feasibility Prediction - Design Document

Portfolio prototype on synthetic data. Companion: [README](../README.md), [slides](Project_Feasibility_ML.pptx).

## 1. Problem and goals
An intake board reviews proposed projects. Feasibility judgements are inconsistent and hard to explain.
Goals: a **calibrated probability** that a project will be delivered feasibly, the **drivers** behind it in
business language, **mitigations**, and monitoring that tells the data science team when inputs drift.

**Users:** project managers, portfolio directors / PMO, the data scientist who owns the model, and read-only
stakeholders - see section 7 and the [README](../README.md#who-uses-it).

## 2. Architecture
```
data/raw/projects.csv -> validate -> clean -> FeatureBuilder -> ColumnTransformer -> model   (feasibility/train.py)
                                                         -> models/feasibility_model.joblib + model_card.json
FastAPI :8004 / Streamlit :8504 / CLI
  /predict -> ProjectInput (pydantic ranges) -> pipeline.predict_proba -> drivers (coef x standardised value)
           -> OOD warnings -> drift window (PSI)
  /advise  -> LangGraph advisor: guard_notes -> predict (tool) -> retrieve playbook (BM25) -> LLM advice -> numeric grounding
```

### Where LLMs are (and are not) used
The decision is made by an interpretable model trained on structured data - an LLM adds no accuracy there and
would make the score non-reproducible. LangGraph/LangChain are used only for the **advisor**, which explains the
model's drivers and retrieves mitigations. RAG is a 7-section playbook keyed by the drivers, so **BM25 without a
vector store** is sufficient.

## 3. Data, validation and cleaning
Synthetic history: 1,212 rows from a hidden logistic process with planted problems. The validation report
(stored in the model card) found exactly what was planted:

| Check | Found | Fix |
|---|---|---|
| Duplicate rows | 12 | dropped |
| Missing values | budget 48, resources 50, dependencies 48, experience 50 | median imputation inside the pipeline |
| Out of range | budget 7 (entered x1000), TRL 6 (code 0) | budget / 1000; TRL -> missing |
| Category spelling | `AI_ML`, `APPLICATION`, ... | lower-cased |

## 4. Features
Raw: complexity, budget, timeline, TRL, resource availability, dependencies, team experience, stakeholders,
project type, region. Engineered in a scikit-learn transformer (same code at train and serve time):
`log_budget_per_week`, `complexity_x_dependencies`, `staffing_pressure` = complexity / (resources + 0.1),
`experience_per_complexity`. A `readiness_gap = 9 - TRL` feature was **removed**: it is perfectly collinear with
TRL and split one effect into two opposite coefficients, hurting interpretability.

## 5. Model selection
| Model (5-fold CV ROC-AUC) | AUC |
|---|---|
| Logistic regression (default) | 0.837 |
| **Logistic regression (tuned: L2, C = 0.1)** | **0.841** |
| Random forest | 0.823 |
| Gradient boosting | 0.820 |
| SVM (RBF) | 0.814 |

Rule: choose logistic regression if it is within 0.02 AUC of the best model - here it is the best outright.
GridSearchCV searched C in {0.01 ... 10} and `l1_ratio` in {0 (L2), 0.5 (elastic net), 1 (L1)}.

### Hold-out test (240 projects)
| ROC-AUC | PR-AUC | Accuracy | Precision | Recall | F1 | Brier |
|---|---|---|---|---|---|---|
| 0.874 | 0.837 | 0.779 | 0.758 | 0.721 | 0.739 | 0.144 |

Calibration (mean predicted -> observed): 0.09 -> 0.07, 0.30 -> 0.26, 0.51 -> 0.56, 0.69 -> 0.68, 0.89 -> 0.93.
Threshold sweep (`eval/results/eval_report.json`): 0.45 maximises F1 (0.772); 0.65 gives precision 0.85 for a
conservative board - the threshold is a business choice exposed in config.

Top drivers (odds ratio per standard deviation): TRL x2.40, complexity x0.58, budget per week x1.62,
staffing pressure x0.67, team experience x1.45, AI/ML project type x0.69.

## 6. Serving, explanation and monitoring
- Per-prediction **drivers**: coefficient x standardised feature value (exact for logistic regression).
- **Out-of-distribution** warning when any input is outside the training range.
- **Drift**: rolling window of recent inputs; PSI per feature against the training histogram saved in the model
  card (stable < 0.1 <= moderate < 0.25 <= significant). Verified: a random training sample scores ~0.02;
  complexity shifted +3 scores 2.39.
- **Metrics** (`/metrics`): requests by endpoint and role, predictions by risk band, OOD inputs, latency.
- **LangSmith** traces of advisor runs; **audit log** of every prediction.

## 7. Roles
| Role | Capabilities |
|---|---|
| project_manager | predict, advise |
| portfolio_director | predict, advise, batch |
| data_scientist | predict, batch, model card, drift, retrain |
| stakeholder_viewer | predict (score only) |

## 8. Guardrails
Pydantic input schema (types, categories, ranges -> HTTP 422); OOD warnings; advisor notes checked for prompt
injection; advisor output numeric grounding; decision-support framing (never "approved").

## 9. Testing and evaluation
11 pytest tests (data validation and cleaning, feature builder, model card and coefficient signs, prediction
ordering, input guardrails, PSI, advisor retrieval / injection / grounding with a fake LLM, API roles).
`python -m eval.run_eval` writes metrics, comparison, threshold sweep and scores for 8 new projects.
RAGAS is not applicable to the classifier (no retrieval-augmented generation in the decision path).

## 10. Tech stack and limitations
scikit-learn 1.9, pandas, numpy, joblib, FastAPI, Streamlit, LangGraph + LangChain + Ollama (advisor only),
LangSmith. Limitations: synthetic labels; no fairness attributes in the data (none should be used for project
feasibility); retraining is manual (`POST /retrain`).
