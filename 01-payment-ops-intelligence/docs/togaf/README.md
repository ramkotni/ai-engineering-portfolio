# Payment Operations Intelligence - TOGAF ADM Delivery Package

Planning and delivery package for taking the **Payment Operations Intelligence** prototype (this folder's parent)
to a production-grade service, structured by the TOGAF 10 Architecture Development Method.

> **Basis.** The project context the master prompt (`/prompt.md`) leaves blank is filled from this project's
> README, `docs/DESIGN.md` and code. Anything not in the repo is an **ASSUMPTION** (marked `A-xx`); every
> estimated number is marked **ESTIMATE** with its formula. The prompt's "ask 10 questions, then pause per phase"
> steps were skipped by agreement; the open questions are listed at the end of each file instead.
> The data is synthetic; the numbers describe a hypothetical production roll-out, not prototype results.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | Payment Operations Intelligence assistant |
| Problem | Failed / duplicate / late payments investigated by hand across tickets, reports, runbooks; repeat incidents; hidden month-end trends |
| AI type | Multi-agent (LangGraph supervisor) GenAI + RAG (CSV + HTML) + deterministic pandas analytics; read-only |
| Users / volume | ~40 ops analysts, managers, auditors, execs, contractors (A-01). ESTIMATE 300 questions/day, peak 10 concurrent |
| Cloud | AWS target (Bedrock path exists in config); prototype runs locally on Ollama |
| Stack | Python 3.12, LangGraph, LangChain, ChromaDB + BM25, pandas, FastAPI, Streamlit, LangSmith, RAGAS |
| Data | Incident exports (CSV), monitoring reports (HTML), runbook (Markdown). Sensitivity: bank/routing numbers, vendor data, amounts (PCI-adjacent, financial PII) |
| Compliance | SOX audit trail, PCI DSS scope-avoidance, GDPR/CCPA for personal data, SOC 2, internal AI policy (A-02) |
| Budget / timeline | ESTIMATE ~USD 0.6M build, 6 months to GA (see 06) |
| Team | Recommended in 06 |
| Integrations | SSO/IdP (replaces demo API keys), ITSM tool for incident export, gateway/ERP monitoring exports, SIEM |

## Files
| # | File | TOGAF phase |
|---|---|---|
| 00 | [00-preliminary.md](00-preliminary.md) | Preliminary |
| 01 | [01-architecture-vision.md](01-architecture-vision.md) | A - Vision |
| 02 | [02-business-architecture.md](02-business-architecture.md) | B - Business |
| 03 | [03-information-systems.md](03-information-systems.md) | C - Data + Application |
| 04 | [04-technology-architecture.md](04-technology-architecture.md) | D - Technology |
| 05 | [05-opportunities-solutions.md](05-opportunities-solutions.md) | E - Opportunities & Solutions |
| 06 | [06-migration-planning.md](06-migration-planning.md) | F - Resources, cost, schedule |
| 07 | [07-product-backlog.md](07-product-backlog.md) | Backlog |
| 08 | [08-functional-spec.md](08-functional-spec.md) | Functional spec |
| 09 | [09-test-strategy.md](09-test-strategy.md) | Test strategy and cases |
| 10 | [10-cicd-mlops.md](10-cicd-mlops.md) | CI/CD and LLMOps |
| 11 | [11-deployment-operations.md](11-deployment-operations.md) | G and H - Deploy, operate, govern |
| 12 | [12-requirements-summary.md](12-requirements-summary.md) | Requirements, ADRs, risks, executive summary |

ID scheme: `REQ-PAY-nnn`, `US-PAY-nn`, `TC-PAY-nn`, `ADR-PAY-nn`, `R-PAY-nn`.
