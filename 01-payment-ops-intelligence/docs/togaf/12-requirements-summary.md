# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-PAY-001 | F | Provide probable root causes citing retrieved incident IDs | Must |
| REQ-PAY-002 | F | Recommend actions citing runbook rules/incidents | Must |
| REQ-PAY-003 | F | Compute trends in code (pandas); LLM narrates only | Must |
| REQ-PAY-004 | F | Role-tailored summaries (executive/operational) | Should |
| REQ-PAY-005 | F | Similar-incident search with metadata filters | Must |
| REQ-PAY-006 | F | Intent-level RBAC per role | Must |
| REQ-PAY-007 | F | Mask amounts for roles without financial visibility | Must |
| REQ-PAY-008 | F | Refuse payment-modifying commands (read-only) | Must |
| REQ-PAY-009 | F | Block prompt injection before any LLM call | Must |
| REQ-PAY-010 | F | Redact bank numbers, emails, phones in input/output | Must |
| REQ-PAY-011 | F | Numeric grounding of every answer | Must |
| REQ-PAY-012 | F | Incident-ID grounding | Must |
| REQ-PAY-013 | F | Audit log for every request | Must |
| REQ-PAY-014 | F | Prometheus metrics endpoint | Must |
| REQ-PAY-015 | F | Capture user feedback | Should |
| REQ-PAY-016 | NF | p95 latency <= 20 s; 10 concurrent users | Must |
| REQ-PAY-017 | NF | 99.5% availability; RTO 4 h / RPO 24 h; canary + rollback | Must |
| REQ-PAY-018 | NF | CI eval gate blocks quality regressions | Must |
| REQ-PAY-019 | F | Scheduled incremental ingestion | Must |
| REQ-PAY-020 | F | SSO with group-to-role mapping, default deny | Must |
| REQ-PAY-021 | NF | TLS 1.2+, KMS encryption, secrets manager | Must |
| REQ-PAY-022 | NF | WCAG 2.1 AA | Should |
| REQ-PAY-023 | NF | LLM spend alerting | Should |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 02, 03 | Search + RCA agents, guard_output | unit, eval gate |
| 002 | 02 | 04, 05 | Recommendation agent | unit, eval |
| 003 | 04 | 08, 10 | analytics.py, Trend agent | unit |
| 004 | 05 | 11, 12 | Summary agent | integration |
| 005 | 03 | 06, 07 | retrieval.py | eval gate |
| 006 | 02, 05, 06 | 05, 12, 15 | rbac.py, authorize node | unit, API test |
| 007 | 06 | 13, 40 | guard_output | integration, security |
| 008 | 07 | 16, 17 | guard_input | unit, red team |
| 009 | 07 | 18, 20 | guard_input | red team |
| 010 | 07 | 19 | guardrails.py | security |
| 011 | 01, 04 | 09 | guard_output | unit |
| 012 | 01 | 02 | guard_output | unit |
| 013 | 08 | 21 | observability.py | integration |
| 014 | 08 | 22 | api.py /metrics | API test |
| 015 | 11 | 27 | /feedback | API test |
| 016 | NFR-1 | 30, 31, 32 | whole stack | staging load |
| 017 | 13 | 29, 34 | IaC, ECS, CodeDeploy | CD, DR drill |
| 018 | 12 | 28, 35, 36, 38 | eval/ | CI eval gate |
| 019 | 09 | 23, 24, 25 | ingest.py | integration |
| 020 | 10 | 26 | ALB OIDC, rbac | E2E |
| 021 | NFR-4 | ZAP scan | infra | security scans |
| 022 | NFR-5 | 33 | UI | staging |
| 023 | NFR-6 | 41 (to add) | CloudWatch | staging |

## Architecture decision records
| ID | Decision | Alternatives rejected | Consequence |
|---|---|---|---|
| ADR-PAY-01 | Deterministic plan per intent in LangGraph | LLM-chosen tool loop | Predictable cost and audit; less flexible for novel asks |
| ADR-PAY-02 | Bedrock hosted Claude, behind `llm.py` | OpenAI, self-hosted Llama | In-region data path; vendor dependency mitigated by abstraction |
| ADR-PAY-03 | OpenSearch managed hybrid search | Chroma server, pgvector, Pinecone | Higher base cost; HA and BM25+kNN natively |
| ADR-PAY-04 | pandas for all numbers | LLM computing figures | Verifiable; narrative limited by grounding |
| ADR-PAY-05 | Read-only assistant | Allow approved actions | Lower risk; ticket drafts (human approved) deferred to Phase 2 |
| ADR-PAY-06 | ECS Fargate | EKS, Lambda | Simple ops for 3 services |
| ADR-PAY-07 | One chunk per incident row | Fixed-size chunking | Keeps symptom/cause/resolution together |
| ADR-PAY-08 | Eval gate in CI | Manual review only | Slower PRs; safer prompt changes |

## Consolidated risk register
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-PAY-01 | Hallucinated root cause | Grounding, citations, feedback, eval gate | AI Lead |
| R-PAY-02 | Retrieval bias to frequent categories | Per-category eval, filters | AI Lead |
| R-PAY-03 | Data leakage | Redaction, masking, VPC endpoints, no provider training | Security |
| R-PAY-04 | Drift | Weekly eval, triggers | AI Lead |
| R-PAY-05 | Vendor lock-in | `llm.py`, Ollama path | Architect |
| R-PAY-06 | High latency | Hosted model, cache, async | Tech Lead |
| R-PAY-07 | Prompt injection via incidents | Input guard, data/instruction separation, TC-20 | Security |
| R-PAY-08 | ITSM access delay | File drop interim | Product Owner |
| R-PAY-09 | Judge model weak (3B could not score faithfulness) | Bedrock judge | AI Lead |
| R-PAY-10 | Cost overrun (LLM, OpenSearch) | Alerts, caching, right-sizing | DevOps |
| R-PAY-11 | Adoption: analysts distrust answers | Pilot, citations, feedback | Product Owner |

## Executive summary
**What:** a read-only, multi-agent assistant that explains failed payments, recommends runbook actions, computes trends and drafts leadership summaries, always citing incidents or rules.
**Why:** faster root cause, fewer repeats, earlier trend detection. Targets are to be measured in a pilot.
**Prototype status:** 29 tests, 100% guardrail block precision/recall on 12 cases, retrieval hit@6 = 1.0 on 10 questions (synthetic data); RCA latency ~150 s on CPU is the main gap.
**Plan:** 6 months, ~8 FTE peak, AWS (Bedrock, OpenSearch, ECS), SSO, nightly ingestion, CI eval gate.
**Cost (ESTIMATE):** build ~USD 0.51M plus 15% contingency; 12-month TCO ~USD 0.82M; 3-year ~USD 1.57M; LLM usage only ~USD 180/month.
**Decisions needed:** budget approval, ITSM access, SSO group design, compliance sign-off on data classes.
**Top risks:** hallucination, latency, data leakage.

## Open questions (consolidated)
Baseline KPIs; real volumes; regulatory scope; ITSM tool; approved cloud/region; rate card; UI accessibility approach; out-of-hours support.
