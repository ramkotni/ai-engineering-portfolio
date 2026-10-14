# Supply Chain Knowledge Assistant - TOGAF ADM Delivery Package

Planning and delivery package for taking the **Supply Chain Knowledge Assistant** prototype to a production,
GxP-aware service, structured by the TOGAF 10 ADM.

> **Basis.** Blank fields of `/prompt.md` are filled from this project's README, `docs/DESIGN.md` and code. Anything
> not in the repo is an **ASSUMPTION** (`A-xx`); every estimated number is marked **ESTIMATE** with its formula. The
> prompt's "ask questions, pause per phase" steps were skipped by agreement; open questions close each file. Data is
> synthetic (fictional products, lots, sites, suppliers); numbers describe a hypothetical production roll-out.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | Supply Chain Knowledge Assistant |
| Problem | Controlled documents in five formats; key facts inside figures (flowcharts, maps, temperature charts); confidential content must not reach external partners |
| AI type | Multimodal RAG, single-agent LangGraph workflow (guard, classify, authorize, retrieve, grade, generate, verify); vision captions of extracted images; versioned prompt templates |
| Users / volume | ~150 users: planners, QA, regulatory, external 3PL/carrier users (A-01). ESTIMATE 400 questions/day, peak 15 concurrent (excursion events spike) |
| Cloud | AWS target; prototype local on Ollama |
| Stack | Python 3.12, LangGraph, ChromaDB + BM25, pdfplumber, PyMuPDF, python-docx, BeautifulSoup, Ollama (`llama3.2`, `nomic-embed-text`, `gemma3:4b`), FastAPI, Streamlit |
| Data | SOPs (PDF), deviation reports (Word), supplier status (HTML), policy (Markdown), lot data (CSV). Classification: public / internal / confidential. Not patient data |
| Compliance | GxP: GDP, EU GMP Annex 11 / 21 CFR Part 11 (electronic records, audit trail), computer-system validation (CSV/CSA), SOC 2, GDPR (user data), EU AI Act (limited risk, A-02) |
| Budget / timeline | ESTIMATE ~USD 0.97M build (people + 20% contingency), 8 months to GA (validation adds time) |
| Integrations | Document management system (DMS/QMS), WMS/ERP lot data, IdP/SSO, partner portal |

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
| 10 | [10-cicd-mlops.md](10-cicd-mlops.md) | CI/CD, LLMOps |
| 11 | [11-deployment-operations.md](11-deployment-operations.md) | G, H |
| 12 | [12-requirements-summary.md](12-requirements-summary.md) | Requirements, ADRs, risks, summary |

ID scheme: `REQ-SCK-nnn`, `US-SCK-nn`, `TC-SCK-nn`, `ADR-SCK-nn`, `R-SCK-nn`.
