# Robotics Fleet Assistant - TOGAF ADM Delivery Package

Planning and delivery package for taking the **Robotics Fleet Assistant** prototype to a production service,
structured by the TOGAF 10 ADM.

> **Basis.** Blank fields of the master prompt (`/prompt.md`) are filled from this project's README, `docs/DESIGN.md`
> and code. Anything not in the repo is an **ASSUMPTION** (`A-xx`); every estimated number is marked **ESTIMATE**
> with its formula. The prompt's "ask questions, pause per phase" steps were skipped by agreement; open questions
> are listed at the end of each file. Data is synthetic; numbers describe a hypothetical production roll-out.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | Robotics Fleet Assistant |
| Problem | 40 AMRs in 4 zones: look-alike failures, calendar-based maintenance, uneven workload, hand-written shift reports |
| AI type | Multi-agent (LangGraph supervisor, 8 agents) + RAG over incidents/maintenance/guide + deterministic pandas/numpy analytics; advisory only |
| Users / volume | ~60 users across technicians, shift leads, managers, execs, contractors (A-01). ESTIMATE 250 questions/day, peak 12 concurrent at shift change |
| Cloud | AWS target; prototype local on Ollama |
| Stack | Python 3.12, LangGraph, ChromaDB + BM25, pandas/numpy, FastAPI, Streamlit, LangSmith, RAGAS |
| Data | Incident events, maintenance logs, robot registry, battery telemetry (time series), troubleshooting guide. Sensitivity: operational, safety-relevant; no PII except emails/phones in notes |
| Compliance | ISO 10218 / ISO 3691-4 safety-system integrity (advice must never weaken it), SOC 2, GDPR (staff data), contractor data-sharing terms (A-02) |
| Budget / timeline | ESTIMATE ~USD 0.5M, 6 months to GA |
| Integrations | Fleet console/WMS (event + telemetry export), CMMS (maintenance logs), IdP/SSO, shift-handover tooling |

## Files
| # | File | TOGAF phase |
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
| 10 | [10-cicd-mlops.md](10-cicd-mlops.md) | CI/CD, LLMOps |
| 11 | [11-deployment-operations.md](11-deployment-operations.md) | G, H |
| 12 | [12-requirements-summary.md](12-requirements-summary.md) | Requirements, ADRs, risks, summary |

ID scheme: `REQ-FLT-nnn`, `US-FLT-nn`, `TC-FLT-nn`, `ADR-FLT-nn`, `R-FLT-nn`.
