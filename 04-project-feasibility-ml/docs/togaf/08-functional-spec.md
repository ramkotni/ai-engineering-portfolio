# 08 - Functional Specification

## Modules
| Module | Inputs | Processing | Outputs | Validations / errors |
|---|---|---|---|---|
| Input validation (`ProjectInput`) | JSON | Pydantic: project_type in {application, infrastructure, data_platform, ai_ml, integration}; region in {americas, emea, apj}; complexity 1-10; budget_usd 10,000-20,000,000; timeline_weeks 2-260; tech_readiness 1-9; resource_availability 0-1; dependency_count 0-50; team_experience_years 0-40; stakeholder_count 1-200; project_id <= 40 chars | validated object | Violation -> HTTP 422 with field |
| Feature builder | validated fields | log_budget_per_week, complexity_x_dependencies, staffing_pressure = complexity/(resources+0.1), experience_per_complexity (identical at train/serve) | feature frame | Missing optional values imputed by pipeline median |
| Scoring | features | `predict_proba` of production model; band by thresholds | probability, band, model version | Model not loaded -> 503 |
| Explanation | features, coefficients | driver = coefficient x standardised value; top 5 by magnitude; direction + plain-language label | drivers | - |
| OOD check | raw values vs training ranges | Flag any feature outside [min, max] | warnings | - |
| Drift window | inputs | Rolling window; PSI vs training histograms | status per feature | Window < 30 -> "insufficient data" |
| Batch | up to 500 projects | Per-row validation and scoring; ranked | list + row errors | > 500 -> 413 |
| Advisor | project, notes | guard_notes (injection screening) -> predict tool -> BM25 playbook retrieval keyed by drivers -> LLM advice -> numeric grounding | advice with playbook citations | Injection -> notes dropped; LLM failure -> verbatim excerpts |
| Training pipeline | warehouse extract | validate, clean, features, CV compare (LR, RF, GB, SVM), GridSearchCV (C, L1/L2/elastic net), selection rule, hold-out eval, calibration, model card | candidate in registry | Failed validation or < 800 rows -> fail |
| Promotion | candidate | Compare with production on time-based hold-out and subgroup gaps | approval request | Gap > 0.05 AUC blocks |
| Monitoring jobs | prediction log, outcomes | PSI weekly; calibration monthly; subgroup report | dashboards, alerts | - |
| Observability | every call | metrics, audit, LangSmith (advisor) | - | Never fails request |

## Roles and permissions
| Role | predict | advise | batch | model | drift | retrain / promote |
|---|---|---|---|---|---|---|
| project_manager | Y | Y | N | N | N | N |
| portfolio_director | Y | Y | Y | N | N | N (sets threshold) |
| data_scientist | Y | N | Y | Y | Y | retrain Y; promotion requires Model Risk |
| stakeholder_viewer | score only | N | N | N | N | N |
| model_risk (new) | N | N | N | Y | Y | approve promotion |

## UI behavior
Form with units and ranges; live validation; result card: probability gauge, risk band, top drivers (bar chart with direction), warnings (OOD, borderline), model version and "decision support only" note; Advise button (hidden for viewers); Batch upload with ranked table and downloadable CSV; Model tab (data scientists): metrics, calibration plot, PSI table. Viewer sees only the probability and band.

## AI behavior specification
| Aspect | Spec |
|---|---|
| Model output | Probability with 2 decimals, band: low >= 0.65, medium 0.45-0.65, high < 0.45 (thresholds from config, see BR-2) |
| Wording | "Likely feasible / needs mitigation / high risk"; never "approved" or "rejected" |
| Advisor tone | Practical, concise; 3-5 mitigations, each tied to a driver and a playbook section |
| Citations | `[playbook: section]`; numbers must match the model output |
| Refusals | Requests to approve/reject, to change the score, or injection attempts: "I can only explain the model's drivers and suggest mitigations." |
| Confidence / abstention | OOD warning present -> advice includes "inputs unusual; manual review"; borderline (within 0.1 of threshold) flagged |
| Fallback to human | OOD, borderline, advisor failure or high-risk band -> PMO analyst review before board |

## Open questions
Final band thresholds; whether the board wants a "confidence interval" display (needs bootstrap or conformal approach).
