# PlantAssist - TOGAF ADM Delivery Package

Planning and delivery package for taking the **PlantAssist** routed-RAG prototype to a production,
safety-critical manufacturing service, structured by the TOGAF 10 ADM.

> **Basis.** Blank fields of `/prompt.md` are filled from this project's README, `docs/DESIGN.md` and code. Anything
> not in the repo is an **ASSUMPTION** (`A-xx`); every estimated number is marked **ESTIMATE** with its formula. The
> prompt's "ask questions, pause per phase" steps were skipped by agreement; open questions close each file. The 13
> plant documents are synthetic; numbers describe a hypothetical production roll-out.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | PlantAssist |
| Problem | Answers live in three document sets (safety, maintenance, quality) owned by three teams; supervisors know the question, not the binder; a maintenance answer omitting lockout/tagout is a safety risk |
| AI type | Agentic **routed RAG** (LangGraph): analyze, route (LLM + policy), parallel hybrid retrieval per source, relevance gate, corrective rewrite, generate, grounding check, finalize/escalate |
| Users / volume | ~250 supervisors, technicians, quality engineers, EHS managers and contractors across 3 shifts (A-01). ESTIMATE 600 questions/day, peak 25 concurrent at shift start |
| Cloud | AWS target (Bedrock Claude + Titan embeddings; repo has Bedrock policy and App Runner trust files, AgentCore path); prototype local on Ollama |
| Stack | Python 3.12, LangGraph, LangChain, ChromaDB + BM25, PyYAML, python-docx, pdfplumber, FastAPI, Streamlit, LangSmith, RAGAS |
| Data | 13 controlled documents (12 Markdown + 1 Word) in safety, maintenance, quality; sensitivity: internal; safety content is life-safety critical. Emails/phones redacted |
| Compliance | OSHA 29 CFR 1910.147 (lockout/tagout) and plant EHS rules, ISO 45001, ISO 9001 document control, SOC 2, GDPR (employee data), EU AI Act (not high-risk by itself, but safety-component adjacency is reviewed, A-02) |
| Budget / timeline | ESTIMATE ~USD 0.65M build (people + 15% contingency), 6 months to GA |
| Integrations | Document management/QMS (controlled documents), IdP/SSO with plant roles, MES/CMMS (Phase 2: asset context), tablet devices on the floor |

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

ID scheme: `REQ-PLA-nnn`, `US-PLA-nn`, `TC-PLA-nn`, `ADR-PLA-nn`, `R-PLA-nn`.
