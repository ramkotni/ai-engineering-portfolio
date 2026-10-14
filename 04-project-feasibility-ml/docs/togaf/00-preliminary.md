# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Evidence |
|---|---|---|
| Business | **Decision support, never the decision.** Output is a feasibility score with drivers; the PMO board decides; wording never says "approved" | Decision-support framing |
| Business | Consistency and explainability over marginal accuracy | LR chosen if within 0.02 AUC of best |
| Business | The threshold is a business choice, owned by the portfolio director and visible in config | Threshold sweep (0.45 max F1, 0.65 conservative) |
| Data | Same code at train and serve time | `FeatureBuilder` in the pipeline |
| Data | Data problems are reported, not hidden | Validation report stored in the model card |
| Data | No protected or personal attributes in features; proxies reviewed | Fairness review (file 09) |
| Application | The model decides; the LLM only explains | LLM is outside the decision path |
| Application | Every prediction has drivers, OOD flags and a drift window | Explainability and monitoring |
| Technology | Models are versioned artifacts with a model card, not files on a laptop | joblib + model card -> registry |
| Technology | Monitored, not trusted blindly: drift, calibration, outcome tracking | PSI; outcomes feedback loop |
| Responsible AI | Human oversight, contestability (PM can see drivers and challenge) | Advice + drivers |
| Responsible AI | Advisor numbers must be grounded in the model output | Numeric grounding |

## Governance and RACI
| Activity | Portfolio Director (PO) | Enterprise Architect | Model Owner (Data Scientist) | Model Risk / Compliance | Security | PMs |
|---|---|---|---|---|---|---|
| Scope | A | C | C | C | I | C |
| Architecture / ADRs | C | A | R | C | C | I |
| Model approval for production | C | I | R | A | I | I |
| Decision threshold | A | I | R | C | I | C |
| Retraining and promotion | C | C | R | A (approve) | I | I |
| Advisor prompt/playbook | C | I | R | C | C | A (content: PMO) |
| Go-live | A | C | R | R | R | I |

**ARB / Model Risk Committee:** monthly; ad hoc on any promotion of a new model version, threshold change or new feature. Independent validation (second data scientist or Model Risk) before first production use.

## Tailored ADM
Light Preliminary/A. B concentrates on the intake process and board decision. C separates data (history, features) from application (scoring, advisor). D adds ML-specific platform pieces (training job, registry). E/F: MVP -> Phase 2 (outcome feedback, scheduled retrain) -> Target (what-if portfolio optimisation). G/H integrate with model risk change control.

## Assumptions and open questions
- A-01 ~120 users; A-02 not a regulated high-risk AI use; internal model-risk policy applies by analogy.
- Q: Does the PMO have a defined "success" label (on-time, on-budget, benefits)? The synthetic label is a single flag.
- Q: Are historical outcomes biased by who got funded (selection bias, funded projects only)?
