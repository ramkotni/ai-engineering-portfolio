# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-FEA-001 | F | Deterministic feasibility probability and risk band | Must |
| REQ-FEA-002 | F | Input validation with business ranges (HTTP 422) | Must |
| REQ-FEA-003 | F | Per-prediction drivers (coefficient x standardised value) | Must |
| REQ-FEA-004 | F | OOD warnings | Must |
| REQ-FEA-005 | F | Playbook-grounded mitigation advice | Should |
| REQ-FEA-006 | F | Advisor injection screening, numeric grounding, fallback | Must (if advisor on) |
| REQ-FEA-007 | F | Batch scoring with ranking and per-row errors | Must |
| REQ-FEA-008 | F | Configurable decision threshold; no "approved" wording | Should |
| REQ-FEA-009 | F | Training validation report and cleaning | Must |
| REQ-FEA-010 | F | Model comparison and interpretability selection rule | Must |
| REQ-FEA-011 | F | Registry with approval-gated promotion and rollback | Must |
| REQ-FEA-012 | F | PSI drift monitoring | Must |
| REQ-FEA-013 | F | Outcome-based performance monitoring | Must |
| REQ-FEA-014 | F | Subgroup/fairness metrics gate | Must |
| REQ-FEA-015 | F | SSO-based capability enforcement | Must |
| REQ-FEA-016 | F | Prediction audit trail | Must |
| REQ-FEA-017 | F | Feedback capture | Could |
| REQ-FEA-018 | NF | CI model-quality gate | Must |
| REQ-FEA-019 | NF | 99.5% availability; canary + rollback; RTO 4 h / RPO 24 h | Must |
| REQ-FEA-020 | NF | `/predict` p95 <= 300 ms; `/advise` p95 <= 20 s | Must |
| REQ-FEA-021 | NF | TLS 1.2+, KMS, secrets manager | Must |
| REQ-FEA-022 | NF | WCAG 2.1 AA | Should |
| REQ-FEA-023 | NF | Advisor spend alert | Could |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 03 | predict.py, pipeline | unit |
| 002 | 01 | 02 | ProjectInput | unit, API |
| 003 | 02 | 04, 05 | predict.py drivers | unit |
| 004 | 03 | 06 | OOD check | integration |
| 005 | 04 | 07 | advisor.py | AI eval |
| 006 | 04 | 08, 09, 10 | advisor guards | red team |
| 007 | 05 | 11, 12 | `/predict/batch` | API |
| 008 | 06 | 13, 14 | config, response wording | unit |
| 009 | 07 | 15 | data.py | integration |
| 010 | 07 | 16, 17 | train.py | integration |
| 011 | 08 | 18, 19 | registry, serving loader | security |
| 012 | 09 | 20 | drift.py | unit |
| 013 | 10 | 21 | monitoring job | integration |
| 014 | 11 | 22, 38 | evaluation job | ML gate |
| 015 | 12 | 23 | rbac | security |
| 016 | 12 | 24 | observability | integration |
| 017 | 13 | 25 | `/feedback` | API |
| 018 | 14 | 26, 27, 34-37 | eval/ | CI gate |
| 019 | 15 | 28, 33 | IaC, ECS | CD, DR |
| 020 | NFR-1 | 29, 30, 31 | stack | load |
| 021 | NFR-4 | ZAP | infra | scans |
| 022 | NFR-5 | 32 | UI | staging |
| 023 | NFR-6 | 41 (to add) | monitoring | staging |

## ADRs
| ID | Decision | Rejected | Consequence |
|---|---|---|---|
| ADR-FEA-01 | Interpretable logistic regression as the decision model (prototype CV AUC 0.841 vs RF 0.823, GB 0.820, SVM 0.814) | Gradient boosting, LLM classifier | Transparent drivers; may leave small accuracy on the table if real data is non-linear (rule: switch only if > +0.02 AUC and ARB agrees) |
| ADR-FEA-02 | CPU-only training and serving | GPU / deep learning | Low cost; tabular scale |
| ADR-FEA-03 | LLM only for advisory text, outside the decision path | LLM scoring | Reproducible scores |
| ADR-FEA-04 | BM25 over the playbook; no vector DB | Embeddings + vector store | Simple, enough for 7 sections |
| ADR-FEA-05 | MLflow-style registry with approval gates | Model file in Git | Auditable promotion/rollback |
| ADR-FEA-06 | Shadow mode for 3 months before board visibility | Immediate go-live | Delay; measured trust |
| ADR-FEA-07 | Time-based hold-out plus random CV | CV only | More honest estimate under drift |
| ADR-FEA-08 | `readiness_gap` feature removed (collinear with TRL) | Keep both | Cleaner coefficients |
| ADR-FEA-09 | Advisor receives scores/drivers only, not raw proposal text | Full proposal text | Lower leakage and injection surface |

## Consolidated risks
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-FEA-01 | Advisor hallucination | Grounding, playbook-only, fallback | AI Lead |
| R-FEA-02 | Bias through proxies | Subgroup gates, no protected attributes, review | Model Risk |
| R-FEA-03 | Selection bias in history | Time-based validation, shadow mode, documentation | Model Owner |
| R-FEA-04 | Data leakage to LLM | Scores/drivers only | Security |
| R-FEA-05 | Drift | PSI, calibration, triggers | Model Owner |
| R-FEA-06 | Gaming of inputs | Input history, OOD flags | PMO |
| R-FEA-07 | Overreliance on score | Decision-support wording, board rationale | Portfolio Director |
| R-FEA-08 | Poor or few labels | Label workshop, minimum data rule | PMO + Data Eng |
| R-FEA-09 | Validation delay | Early Model Risk engagement | Product Owner |
| R-FEA-10 | Model/threshold changes without governance | Registry approvals, audit | Model Risk |

## Executive summary
**What:** an explainable machine-learning service that scores project proposals for feasibility, shows the drivers, flags unusual inputs, monitors drift and (optionally) suggests playbook-based mitigations through an LLM advisor that stays outside the decision.
**Why:** consistent, defensible intake decisions and mitigation before kickoff. Targets are pilot targets, not prototype results.
**Prototype:** tuned logistic regression, CV AUC 0.841 (best of four), hold-out ROC-AUC 0.874, PR-AUC 0.837, Brier 0.144, well calibrated; 11 tests (synthetic data). Gaps: real labels, selection bias, registry/approval, outcome monitoring.
**Plan:** 5 months, 6.4 FTE peak, AWS (ECS, MLflow, S3/Athena), SSO, 3-month shadow mode, Model Risk validation.
**Cost (ESTIMATE):** build ~USD 0.34M people plus 15% contingency; 12-month TCO ~USD 0.58M; 3-year ~USD 1.14M; infrastructure ~USD 700/month; LLM advisor ~USD 1/month.
**Decisions needed:** label definition, shadow-mode period, validator, ownership of the decision threshold.
**Top risks:** bias, selection bias, drift.

## Open questions (consolidated)
Label definition; outcome maturity; independent validator; warehouse/registry standards; whether rejected proposals have outcome data.
