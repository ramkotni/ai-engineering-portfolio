# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-PLA-001 | F | Answer from the routed source(s) with document, revision and section citations | Must |
| REQ-PLA-002 | F | Citation validity: remove non-existent `[n]`, flag uncited answers | Must |
| REQ-PLA-003 | F | Hands-on maintenance answers include lockout/tagout and PPE from the safety source | Must |
| REQ-PLA-004 | F | Emergency detection with a fixed banner prepended by code | Must |
| REQ-PLA-005 | F | Refuse requests to defeat protections; withhold unsafe model output | Must |
| REQ-PLA-006 | F | Relevance gate (cosine >= 0.55), one rewrite, then escalate with owner contact | Must |
| REQ-PLA-007 | F | Numeric grounding with regeneration and caveat | Must |
| REQ-PLA-008 | F | Routing with confidence fallback (<0.6 searches all allowed sources) and out-of-scope decline | Must |
| REQ-PLA-009 | F | Role-to-source access; safety open to all | Must |
| REQ-PLA-010 | F | Document ingestion with revisions, quarantine of incomplete metadata, table-aware chunking | Must |
| REQ-PLA-011 | F | PII redaction before LLM, logs and traces | Must |
| REQ-PLA-012 | F | Tablet-friendly UI | Must |
| REQ-PLA-013 | F | Audit log of every request | Must |
| REQ-PLA-014 | F | Feedback capture; safety thumbs-down review | Should |
| REQ-PLA-015 | F | SSO with group-to-role mapping, default deny | Must |
| REQ-PLA-016 | NF | CI eval and safety gate | Must |
| REQ-PLA-017 | NF | 99.9% availability in shifts; canary + rollback; degraded verbatim mode; RTO 2 h / RPO 24 h | Must |
| REQ-PLA-018 | NF | p95 <= 15 s; emergency banner <= 1 s; 25 concurrent | Must |
| REQ-PLA-019 | NF | TLS 1.2+, KMS, secrets manager | Must |
| REQ-PLA-020 | NF | LLM spend alerting | Should |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 02 | generate, check_grounding | unit, eval |
| 002 | 01 | 03 | guardrails (citations) | unit |
| 003 | 02 | 04, 05 | router policy, grade_documents | unit, integration |
| 004 | 03 | 06, 07 | analyze_query, finalize | E2E, safety |
| 005 | 04 | 08, 09, 10 | guardrails | red team |
| 006 | 05 | 11 | grade, rewrite, no_answer | integration |
| 007 | 06 | 12 | guardrails (numeric) | unit |
| 008 | 07 | 13, 14, 15 | router | eval gate |
| 009 | 08 | 16, 17 | rbac, retrieval | security |
| 010 | 09 | 18, 19, 20 | loaders, chunking, ingest | integration |
| 011 | 10 | 21 | guardrails (PII) | security |
| 012 | 11 | 22 | UI | UI test |
| 013 | 12 | 23 | observability | integration |
| 014 | 12 | 24 | feedback | API |
| 015 | 13 | 25 | ALB OIDC, rbac | E2E |
| 016 | 14 | 26, 33-36 | eval/ | CI gate |
| 017 | 15 | 27, 32 | IaC, ECS | CD, DR |
| 018 | NFR-1/2 | 28, 29, 30 | stack | load |
| 019 | NFR-4 | ZAP | infra | scans |
| 020 | NFR-6 | 41 (to add) | monitoring | staging |

## ADRs
| ID | Decision | Rejected | Consequence |
|---|---|---|---|
| ADR-PLA-01 | One agentic routed workflow with bounded loops | Multi-agent | Fewer calls; 2-5 LLM calls per question; simpler audit |
| ADR-PLA-02 | Safety-first routing policy (mandatory safety search for emergencies and hands-on work) | Rely on the LLM to include safety | Deterministic safety behaviour; sometimes extra safety text |
| ADR-PLA-03 | Deterministic guardrails first, LLM verifier second | LLM-only verification (3B verifier flagged almost every answer) | Exact numbers; verifier adds latency/cost when on |
| ADR-PLA-04 | One index per source | Single mixed index | Ownership, access and tuning separable; three indices to operate |
| ADR-PLA-05 | Hybrid retrieval with cosine as the absolute relevance gate | Vector only (small embedding models compress scores) | Better exact-term ranking ("gland retainer bolts" #2 -> #1) |
| ADR-PLA-06 | Bedrock Claude + Titan v2 with Bedrock Guardrails plus own rules | Local GPU hosting | Seconds per answer vs minutes on CPU; vendor dependency mitigated by config switch |
| ADR-PLA-07 | ECS Fargate (App Runner / AgentCore as alternatives) | EKS, Lambda | Network controls and WAF; slightly more ops than App Runner |
| ADR-PLA-08 | Emergency answers never cached; banner added by code, not by the LLM | Cache everything | Slightly higher cost; no stale emergency content |
| ADR-PLA-09 | Degraded verbatim mode if LLM is down | Hard failure | Safety information remains available |

## Consolidated risks
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-PLA-01 | Wrong number | Numeric grounding, regeneration, caveat, verifier | AI Lead |
| R-PLA-02 | Misrouting misses safety doc | Safety-first policy, low-confidence fan-out | AI Lead |
| R-PLA-03 | Unsafe advice | Dual guardrails, Bedrock Guardrails, EHS red-team | EHS |
| R-PLA-04 | Stale revision | Revision sync, freshness SLO | Data Eng / owners |
| R-PLA-05 | Source/length bias | Per-source eval | AI Lead |
| R-PLA-06 | Document injection | Data/instruction separation, TC-37 | Security |
| R-PLA-07 | Contractor sees internal content | Role filter in code, TC-16/17 | Security |
| R-PLA-08 | Provider behaviour drift | Pinned models, regression set | AI Lead |
| R-PLA-09 | Lock-in | Config switch | Architect |
| R-PLA-10 | Overreliance | Training, verify prompts, permit-to-work unchanged | Plant Manager |
| R-PLA-11 | Connectivity gaps on the floor | Wi-Fi survey, offline fallback (Phase 2) | IT |
| R-PLA-12 | LLM cost at 18k requests/month | Cache, smaller router model, alerts | DevOps |

## Executive summary
**What:** a routed, cited question-answering assistant for plant supervisors that finds the right procedure across safety, maintenance and quality documents, always attaches lockout/tagout and PPE to hands-on work, shows a fixed emergency banner, refuses to help defeat protections and escalates when documentation does not cover a question.
**Why:** faster, traceable, safer lookups. Pilot targets, not prototype results.
**Prototype:** retrieval hit@5 100% (26/26) and MRR 0.974; guardrail precision/recall 1.0/1.0 on 16 cases; 48 unit + 3 integration tests (synthetic documents). Gaps: 2-4 min per answer on CPU, no SSO, no document sync, RAGAS faithfulness needs a strong judge.
**Plan:** 6 months, 8.75 FTE peak, AWS (Bedrock + Guardrails, OpenSearch, ECS), SSO, document-control sync, EHS red-team, one-shift pilot then all shifts.
**Cost (ESTIMATE):** build ~USD 0.57M people plus 15% contingency; 12-month TCO ~USD 0.95M; 3-year ~USD 1.96M; LLM usage ~USD 770/month (dominant variable cost).
**Decisions needed:** EHS acceptance of AI-generated safety answers (or verbatim-only), document-control API, pilot plant, budget owner.
**Top risks:** wrong number, unsafe advice, stale revision.

## Open questions (consolidated)
Verbatim-only safety mode; languages; offline mode; owner of escalation directory; MDM for tablets; plant-vs-central LLM budget.
