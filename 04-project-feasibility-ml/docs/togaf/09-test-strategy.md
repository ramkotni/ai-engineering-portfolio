# 09 - Test Strategy and Test Cases

## Strategy
| Level / type | Scope | Tools | Env |
|---|---|---|---|
| Unit | validation/cleaning, FeatureBuilder, drivers, PSI, ProjectInput ranges, advisor retrieval | pytest (fake LLM) | CI |
| Integration | training pipeline end to end on synthetic data, registry, API | pytest + TestClient | CI/test |
| API / contract | all endpoints, capabilities | schemathesis | test |
| E2E + UI | PM, director, data scientist flows | Playwright | staging |
| Regression | suite every PR; model-quality gate on any model/feature change | pytest, `eval/run_eval.py` | CI |
| Performance / load / stress / soak | 20 concurrent `/predict`; batch 500; advisor 5 concurrent | Locust | staging |
| Security | OWASP Top 10 and LLM Top 10, injection through `notes`, IDOR on prediction logs, role bypass | ZAP, scripted prompts | staging |
| ML evaluation | CV, hold-out, calibration, threshold sweep, subgroup, stability, sensitivity | `eval/` | CI/nightly |
| Advisor evaluation | grounding, relevance, hallucination, injection, judge | `eval/`, Bedrock judge | nightly |
| Accessibility / usability / UAT | WCAG 2.1 AA; PM and director scenarios | axe, scripts | staging |
| DR / failover | restore registry/artifacts | drills | staging |

Entry: green build, env deployed, data loaded. Exit: no open Sev1/2, Must stories covered, quality gates green, Model Risk validation signed.
Test data: synthetic 1,212 projects with planted problems; 8 unlabelled new projects; adversarial inputs (boundary values, OOD); generated subgroups; real data only in staging after masking.

**ML evaluation (note: RAGAS does not apply to the classifier; the advisor is evaluated separately).** Gates: 5-fold CV ROC-AUC >= 0.80; hold-out ROC-AUC >= 0.80 (prototype 0.874) and PR-AUC >= 0.75 (prototype 0.837); Brier <= 0.18 (prototype 0.144); calibration bins within +/-0.07 of observed (prototype within 0.05); F1 at the chosen threshold reported; **coefficient sign checks** (TRL > 0, resource availability > 0, complexity < 0, dependency interaction < 0); stability across 5 seeds (AUC std <= 0.01); subgroup AUC (type, region) within 0.05 of overall; approval-rate gap by region <= 10 pts unless explained; sensitivity (+/-1 TRL changes probability in the expected direction for 100% of sampled cases). **Advisor:** golden set of 30 profiles; numeric grounding violations = 0; every mitigation maps to a playbook section; injection set 100% blocked; LLM-judge relevance >= 4/5 with 10% human sampling.

## Test cases
| ID | Linked | Title | Preconditions | Steps | Data | Expected | Type | Pri |
|---|---|---|---|---|---|---|---|---|
| TC-FEA-01 | US-01, REQ-001 | Valid prediction | PM | POST /predict | valid JSON | p in [0,1], band, version | API | P1 |
| TC-FEA-02 | US-01, REQ-002 | Out-of-range inputs | PM | complexity=11; TRL=0; budget=5 | boundary set | 422 each | API | P1 |
| TC-FEA-03 | US-01 | Determinism | model loaded | Score twice | same input | Identical output | Unit | P1 |
| TC-FEA-04 | US-02, REQ-003 | Driver math | model | Compare to coef x standardised | sample | Equal | Unit | P1 |
| TC-FEA-05 | US-02 | Viewer limits | viewer | POST /predict | valid | Score only | API | P1 |
| TC-FEA-06 | US-03, REQ-004 | OOD flag | PM | budget per week extreme | OOD input | Warning + counter | Integration | P1 |
| TC-FEA-07 | US-04, REQ-005 | Advice grounded | PM | /advise high-risk | profile | Playbook sections match drivers | AI | P1 |
| TC-FEA-08 | US-04, REQ-006 | Injection in notes | PM | notes "ignore previous..." | set of 20 | Rejected 100% | Security (LLM01) | P1 |
| TC-FEA-09 | US-04 | Numeric grounding | fake LLM invents 0.99 | Run | fixture | Flagged | Unit | P1 |
| TC-FEA-10 | US-04 | LLM down | LLM raises | /advise | profile | Verbatim excerpts | Integration | P2 |
| TC-FEA-11 | US-05, REQ-007 | Batch ranking | director | POST batch 8 | new_projects.csv | Ranked, row errors | API | P1 |
| TC-FEA-12 | US-05 | PM batch denied | PM | POST batch | rows | 403 | API | P1 |
| TC-FEA-13 | US-06, REQ-008 | Threshold audit | director | Change to 0.65 | - | Band changes; audit entry | Integration | P2 |
| TC-FEA-14 | US-06 | Wording check | any | 100 responses | set | No "approved"/"rejected" | Unit | P1 |
| TC-FEA-15 | US-07, REQ-009 | Validation report | pipeline | Run on planted-issue data | CSV | Finds 12 dups, 7 budgets, 6 TRL, spellings | Integration | P1 |
| TC-FEA-16 | US-07, REQ-010 | Selection rule | pipeline | Run | CSV | LR chosen when within 0.02 | Unit | P1 |
| TC-FEA-17 | US-07 | Too few rows | pipeline | 500 rows | CSV | Fails | Integration | P2 |
| TC-FEA-18 | US-08, REQ-011 | Promotion needs approval | candidate | Switch alias w/o approval | - | Denied | Security | P1 |
| TC-FEA-19 | US-08 | Rollback | two versions | Rollback | - | Previous served | Integration | P1 |
| TC-FEA-20 | US-09, REQ-012 | PSI stable and shifted | window | Random sample vs +3 complexity | data | <0.1 vs >=0.25 (prototype 0.02 vs 2.39) | Unit | P1 |
| TC-FEA-21 | US-10, REQ-013 | Outcome metrics | matured outcomes | Run monthly job | fixture | AUC/Brier/slope | Integration | P1 |
| TC-FEA-22 | US-11, REQ-014 | Subgroup gap blocks | skewed model | Promotion | fixture | Blocked | AI | P1 |
| TC-FEA-23 | US-12, REQ-015 | Capabilities | tokens per role | Call endpoints | matrix | 403 where not allowed | Security | P1 |
| TC-FEA-24 | US-12, REQ-016 | Audit entry | any | Predict | - | Fields present, no PII beyond user id | Integration | P1 |
| TC-FEA-25 | US-13, REQ-017 | Feedback | run_id | POST | score | Stored | API | P3 |
| TC-FEA-26 | US-14, REQ-018 | Gate fails | degrade | CI | branch | Fails | Pipeline | P1 |
| TC-FEA-27 | US-14 | Coefficient signs | model | Check | model card | TRL +, complexity - | Unit | P1 |
| TC-FEA-28 | US-15, REQ-019 | Canary rollback | 500s | Deploy | - | Auto rollback | Deployment | P1 |
| TC-FEA-29 | NFR-1, REQ-020 | Load | staging | 20 users 10 min | Locust | p95 <= 300 ms | Load | P1 |
| TC-FEA-30 | NFR-1 | Stress | staging | 100 users | Locust | Graceful | Stress | P2 |
| TC-FEA-31 | NFR-2 | Soak | staging | 8 h | Locust | No leak; drift window bounded | Soak | P3 |
| TC-FEA-32 | REQ-022 | Accessibility | UI | axe, keyboard | pages | No serious issues; charts have text alternative | Accessibility | P2 |
| TC-FEA-33 | REQ-019 | DR | backup | Restore registry | - | RTO <= 4 h | DR | P2 |
| TC-FEA-34 | ML | Hold-out metrics | pipeline | Evaluate | hold-out | AUC >= 0.80 etc. | ML | P1 |
| TC-FEA-35 | ML | Calibration | hold-out | Bins | - | Within 0.07 | ML | P1 |
| TC-FEA-36 | ML | Seed stability | pipeline | 5 seeds | - | AUC std <= 0.01 | ML | P2 |
| TC-FEA-37 | ML | Sensitivity | model | +/-1 TRL | 100 cases | Direction correct | ML | P2 |
| TC-FEA-38 | ML | Fairness by region/type | hold-out | Subgroup AUC | - | Gap <= 0.05 | ML | P1 |
| TC-FEA-39 | UAT | PM scenario | pilot | 10 real proposals | proposals | Drivers judged sensible by >= 8/10 | UAT | P1 |
| TC-FEA-40 | UAT | Shadow comparison | 3 months | Compare to board decisions | decisions | Report accepted by Model Risk | UAT | P1 |

## Traceability (REQ -> TC)
001: 01, 03 | 002: 02 | 003: 04, 05 | 004: 06 | 005: 07, 09, 10 | 006: 08 | 007: 11, 12 | 008: 13, 14 | 009: 15 | 010: 16, 17 | 011: 18, 19 | 012: 20 | 013: 21 | 014: 22, 38 | 015: 23 | 016: 24 | 017: 25 | 018: 26, 27, 34-37 | 019: 28, 33 | 020: 29, 30, 31 | 021: ZAP | 022: 32 | 023: cost alert (add TC-FEA-41).

## Open questions
Who is the independent validator? Minimum number of matured outcomes (30?) before outcome metrics are trusted.
