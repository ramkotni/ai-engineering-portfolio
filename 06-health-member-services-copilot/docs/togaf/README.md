# Health Member Services Copilot - TOGAF ADM Delivery Package

Planning and delivery package for taking the **Evergreen Member Assist** prototype to a HIPAA-regulated production
service, structured by the TOGAF 10 ADM.

> **Basis.** Blank fields of `/prompt.md` are filled from this project's README, code, eval reports and deploy
> scripts. Anything not in the repo is an **ASSUMPTION** (`A-xx`); every estimated number is marked **ESTIMATE**
> with its formula. The prompt's "ask questions, pause per phase" steps were skipped by agreement; open questions
> close each file. Evergreen Health Plans, members, claims and policies are fictional; numbers describe a
> hypothetical production roll-out. This is not legal or compliance advice.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | Evergreen Member Assist (Health Member Services Copilot) |
| Problem | High volume of repetitive benefit and claim-denial questions; answers split between benefit documents and the claims system; PHI must be protected; a member must never see another member's claim |
| AI type | **Multi-agent** (LangGraph supervisor -> policy RAG agent / claims agent / direct response) with grader and **critic loop**, per-session memory, Bedrock Guardrails; deployable to **Bedrock AgentCore Runtime** |
| Users / volume | ~150,000 members (portal/app chat) plus ~120 member-services representatives (A-01). ESTIMATE 3,000 chats/day (~9,000 turns), peak 60 concurrent in open enrollment and Monday mornings |
| Cloud | AWS (Bedrock Claude + Titan v2, Guardrails, Knowledge Bases option, AgentCore Runtime, ECR); local Ollama + Chroma for development |
| Stack | Python 3.12, LangGraph, LangChain, langchain-aws, FastAPI, Chroma / Bedrock Knowledge Bases, LangSmith, pytest (74 tests), GitHub Actions |
| Data | Plan documents (8 policy docs in prototype), claims records (PHI), conversation content. Sensitivity: PHI/PII, health plan confidential |
| Compliance | HIPAA Privacy/Security Rules (AWS BAA), HITRUST/SOC 2, state insurance and claims-communication rules, member-notice and appeal timelines (A-02), GDPR/CCPA where applicable, EU AI Act not applicable to US-only scope (A-03) |
| Budget / timeline | ESTIMATE ~USD 1.5M build (people + 20% contingency), 9 months to GA |
| Integrations | Member identity (CIAM/Cognito, JWT), claims platform (read-only API), plan-document repository, contact-center platform (human handoff), SIEM |

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

ID scheme: `REQ-MSC-nnn`, `US-MSC-nn`, `TC-MSC-nn`, `ADR-MSC-nn`, `R-MSC-nn`.
