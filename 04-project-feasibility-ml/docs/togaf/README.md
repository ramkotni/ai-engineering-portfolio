# Project Feasibility Prediction - TOGAF ADM Delivery Package

Planning and delivery package for taking the **Project Feasibility Prediction** prototype (classical ML plus an
optional LLM advisor) to a production PMO service, structured by the TOGAF 10 ADM.

> **Basis.** Blank fields of `/prompt.md` are filled from this project's README, `docs/DESIGN.md` and code. Anything
> not in the repo is an **ASSUMPTION** (`A-xx`); every estimated number is marked **ESTIMATE** with its formula. The
> prompt's "ask questions, pause per phase" steps were skipped by agreement; open questions close each file. Data is
> synthetic (1,212 generated projects); numbers describe a hypothetical production roll-out.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | Project Feasibility Prediction |
| Problem | PMO funding decisions vary by reviewer; risky projects (low TRL, thin resourcing, many dependencies) are approved and then slip; historical outcomes unused |
| AI type | **Predictive ML** (scikit-learn pipeline, tuned logistic regression, interpretable drivers, OOD flags, PSI drift) + optional **GenAI advisor** (LangGraph, BM25 over a delivery playbook, numeric grounding) |
| Users / volume | ~120 project managers, PMO staff, 3 data scientists, read-only stakeholders (A-01). ESTIMATE 60 new proposals/month, 300 predictions/month incl. what-if, batch of up to 100 |
| Cloud | AWS target; prototype local |
| Stack | Python 3.12, scikit-learn, pandas, joblib, FastAPI, Streamlit, LangGraph + Ollama (advisor), LangSmith |
| Data | Historical project records (structured), intake proposals, delivery playbook. Sensitivity: internal; budgets confidential; no personal data or protected attributes |
| Compliance | Internal model-risk policy (SR 11-7-style: documentation, validation, monitoring), SOC 2, GDPR (reviewer identities in audit), EU AI Act (not a listed high-risk use; transparency and human oversight applied anyway, A-02) |
| Budget / timeline | ESTIMATE ~USD 0.39M build (people + 15% contingency), 5 months to GA |
| Integrations | PPM/portfolio tool (historical outcomes, intake), IdP/SSO, data warehouse, BI |

## Files
| # | File | Phase |
|---|---|---|
| 00 | [00-preliminary.md](00-preliminary.md) | Preliminary |
| 01 | [01-architecture-vision.md](01-architecture-vision.md) | A |
| 02 | [02-business-architecture.md](02-business-architecture.md) | B |
| 03 | [03-information-systems.md](03-information-systems.md) | C |
| 04 | [04-technology-architecture.md](04-technology-architecture.md) | D |
| 05 | [05-opportunities-solutions.md](05-opportunities-solutions.md) | E |
| 06 | [06-migration-planning.md](06-migration-planning.md) | F |
| 07 | [07-product-backlog.md](07-product-backlog.md) | Backlog |
| 08 | [08-functional-spec.md](08-functional-spec.md) | Functional spec |
| 09 | [09-test-strategy.md](09-test-strategy.md) | Tests |
| 10 | [10-cicd-mlops.md](10-cicd-mlops.md) | CI/CD, MLOps |
| 11 | [11-deployment-operations.md](11-deployment-operations.md) | G, H |
| 12 | [12-requirements-summary.md](12-requirements-summary.md) | Requirements, ADRs, risks, summary |

ID scheme: `REQ-FEA-nnn`, `US-FEA-nn`, `TC-FEA-nn`, `ADR-FEA-nn`, `R-FEA-nn`.
