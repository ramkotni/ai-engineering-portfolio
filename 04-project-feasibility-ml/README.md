# 04 - Project Feasibility Prediction

End-to-end **machine learning** pipeline that predicts whether a proposed project is feasible, explains the
prediction, monitors input drift and - optionally - turns the model's drivers into advice with a small
LangGraph agent grounded in a delivery playbook.

> Portfolio prototype. Independent re-implementation of an ML feasibility-prediction pattern on
> **synthetic data** - not employer code or data.

| | |
|---|---|
| **Model** | scikit-learn Pipeline: feature engineering -> impute / scale / one-hot -> **Logistic Regression** (tuned) |
| **Selection** | 5-fold CV ROC-AUC vs Random Forest, Gradient Boosting, SVM; LR chosen if within 0.02 AUC of the best (interpretability) |
| **LLM** | Optional advisor: LangGraph (guard -> predict tool -> playbook retrieval (BM25) -> LLM advice -> numeric grounding) |
| **Test URLs** | API **http://localhost:8004/docs** - UI **http://localhost:8504** - metrics **http://localhost:8004/metrics** |
| **Docs** | [Design document](docs/DESIGN.md) - [Slides](docs/Project_Feasibility_ML.pptx) |

## Sample data (synthetic, committed) - regenerate with `python data/generate_data.py`
- `data/raw/projects.csv` - 1,212 historical projects generated from a hidden logistic process, with planted
  data problems: ~4% missing values, 8 budgets entered x1000, 6 invalid TRL codes, 12 duplicate rows,
  inconsistent category spelling.
- `data/raw/new_projects.csv` - 8 unlabelled projects to score.
- `data/raw/delivery_playbook.md` - mitigation guidance the advisor retrieves.

## Pipeline
1. **Validate** (report every problem) -> **clean** (drop duplicates, normalise categories, repair the budget
   unit error, null-out impossible values) - pandas / numpy.
2. **Feature engineering** (`FeatureBuilder` transformer, identical at train and serve time): budget per week
   (log), complexity x dependencies, staffing pressure, experience per complexity.
3. **Model comparison** with stratified 5-fold CV; **GridSearchCV** over C and L1/L2/elastic-net.
4. **Selection rule**: logistic regression unless another model is > 0.02 AUC better - coefficients map to
   business drivers.
5. **Hold-out evaluation**: ROC-AUC, PR-AUC, accuracy, precision, recall, F1, Brier, confusion matrix, calibration.
6. **Model card** (`models/model_card.json`) with metrics, coefficients, data-validation report, training
   histograms for drift, intended use and limitations.

## Run it
```powershell
cd 04-project-feasibility-ml
pip install -r requirements.txt
python -m feasibility.train                           # ~1 min on CPU; writes models/
python -m feasibility.cli score data/raw/new_projects.csv
uvicorn feasibility.api:app --port 8004               # http://localhost:8004/docs
streamlit run ui/streamlit_app.py --server.port 8504
python -m feasibility.cli advise PRJ-NEW-5            # LLM advisor (needs Ollama llama3.2)
```
```powershell
curl -X POST http://localhost:8004/predict -H "X-API-Key: pm-demo-key" -H "Content-Type: application/json" -d '{
  "project_type": "ai_ml", "region": "emea", "complexity": 8, "budget_usd": 300000, "timeline_weeks": 40,
  "tech_readiness": 3, "resource_availability": 0.4, "dependency_count": 7, "team_experience_years": 3, "stakeholder_count": 12}'
curl http://localhost:8004/model -H "X-API-Key: ds-demo-key"
curl http://localhost:8004/drift -H "X-API-Key: ds-demo-key"
```

## Sample roles
| Role | Demo API key | Capabilities |
|---|---|---|
| `project_manager` | `pm-demo-key` | predict, advise |
| `portfolio_director` | `director-demo-key` | predict, advise, batch |
| `data_scientist` | `ds-demo-key` | predict, batch, model card, drift, retrain |
| `stakeholder_viewer` | `viewer-demo-key` | predict (score only - no drivers or model internals) |

## Guardrails
- **Input schema** (pydantic): types, allowed categories and business ranges -> 422 on invalid input.
- **Out-of-distribution warnings** when an input is outside the training range.
- **Advisor**: prompt-injection check on free-text notes; numeric grounding (numbers must come from the model
  output, project data or playbook); "decision support, not approval" framing.
- **RBAC** on every endpoint.

## Why no RAGAS here
The core is a classifier, not retrieval-augmented generation, so it is evaluated with ML metrics (ROC-AUC,
PR-AUC, F1, calibration, threshold trade-offs). The advisor's only retrieval is a 7-section playbook keyed by
the model's drivers; its output is checked with the numeric-grounding guardrail. RAGAS is used in projects
01, 02, 03 and 05.

## Tests, evaluation, monitoring
```powershell
pytest -q                                  # 11 tests: data, features, model, explanations, guardrails, drift, advisor, API roles
python -m eval.run_eval                    # metrics, model comparison, threshold sweep, scoring of new projects
python -m eval.run_eval --advisor 3        # + advisor grounding check (LLM)
```
Monitoring: `/metrics` (`feasibility_requests_total{endpoint,role}`, `feasibility_predictions_total{band}`,
`feasibility_ood_inputs_total`, latency histogram), `/drift` (PSI per feature vs training: stable < 0.1 <
moderate < 0.25 < significant), LangSmith traces of the advisor (`LANGSMITH_TRACING=true`), `logs/audit.jsonl`.
