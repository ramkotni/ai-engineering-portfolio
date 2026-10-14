# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-MSC-001 | F | Cited benefit answers from plan documents | Must |
| REQ-MSC-002 | F | Retrieval filtered by member plan and plan year | Must |
| REQ-MSC-003 | F | Claim status and denial explanation from the claim record plus policy, with next steps | Must |
| REQ-MSC-004 | F | Claim fields and numbers must match the record/evidence | Must |
| REQ-MSC-005 | F | A member can only access own claims; identical reply for not-found and not-yours | Must |
| REQ-MSC-006 | F | No claim enumeration; possessive/obfuscated attempts refused | Must |
| REQ-MSC-007 | F | Session memory with follow-up rewrite and TTL | Must |
| REQ-MSC-008 | F | PII redaction before model, in logs and traces; output leak check | Must |
| REQ-MSC-009 | F | Prompt-injection/jailbreak defence (local + Bedrock Guardrails) | Must |
| REQ-MSC-010 | F | No medical advice; AI disclosure; always-available human option | Must |
| REQ-MSC-011 | F | Human handoff with context summary and fallback | Must |
| REQ-MSC-012 | F | Identity from verified JWT; request-body member id ignored | Must |
| REQ-MSC-013 | F | Plan-year-aware, idempotent knowledge ingestion | Must |
| REQ-MSC-014 | F | Groundedness critic with bounded regeneration and escalation | Must |
| REQ-MSC-015 | F | Pseudonymised audit log and feedback capture | Must |
| REQ-MSC-016 | NF | CI evaluation and red-team gate | Must |
| REQ-MSC-017 | NF | 99.9% availability; canary + rollback incl. leakage probe; RTO 1 h | Must |
| REQ-MSC-018 | NF | p95 <= 12 s; 60 concurrent; quota headroom | Must |
| REQ-MSC-019 | NF | HIPAA technical safeguards (TLS, KMS, access control, audit, minimum necessary) | Must |
| REQ-MSC-020 | NF | WCAG 2.1 AA; reading grade <= 8 | Must |
| REQ-MSC-021 | NF | LLM spend alerting and cost per conversation tracking | Should |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 03 | retrieve, generate | eval gate |
| 002 | 01, 11 | 02 | KB filter | integration |
| 003 | 02, 03 | 04, 05, 07 | claims_agent, generate | E2E |
| 004 | 02 | 06 | critic, output_guard | unit |
| 005 | 04 | 08 | tools.py | security gate |
| 006 | 04 | 09, 10, 11 | tools.py, input_guard | security gate |
| 007 | 05 | 12, 13 | checkpointer, supervisor | integration |
| 008 | 06 | 14, 15, 16 | guardrails, observability | security gate |
| 009 | 07 | 17, 18, 19 | input_guard, Bedrock Guardrails | red-team gate |
| 010 | 08 | 20, 21 | prompts, UI | AI eval, UI test |
| 011 | 09 | 22, 23 | handoff connector | integration |
| 012 | 10 | 24 | API auth | security |
| 013 | 11 | 25, 26 | ingest.py | integration |
| 014 | 12 | 27 | critic | integration |
| 015 | 13 | 28 | observability, S3 audit | integration |
| 016 | 14 | 29, 37-40 | eval/ | CI gate |
| 017 | 15 | 30, 35, 36 | IaC, AgentCore | CD, DR |
| 018 | NFR-1/2 | 31, 32, 33 | stack | load |
| 019 | NFR-4 | ZAP, 16 | infra | scans |
| 020 | NFR-5 | 34, 39 | UI | staging |
| 021 | NFR-6 | 43 (to add) | monitoring | staging |
(Compliance review TC-MSC-41 and employee beta TC-MSC-42 trace to REQ-MSC-003, 010.)

## ADRs
| ID | Decision | Rejected | Consequence |
|---|---|---|---|
| ADR-MSC-01 | Supervisor + specialist agents with critic loop and bounded rewrites | Single prompt; unbounded autonomous agent | Predictable behaviour and cost; ~3.3 LLM calls per turn |
| ADR-MSC-02 | Bedrock AgentCore Runtime (portable container; Fargate fallback) | Lambda, self-managed EKS | Managed runtime and identity; verify HIPAA eligibility, keep container portable |
| ADR-MSC-03 | Authorization in tools/code, identity from JWT | Prompt-level instructions; body `member_id` | Injection cannot widen access; requires CIAM integration |
| ADR-MSC-04 | Local rules plus Bedrock Guardrails | Local rules only (5 known gaps), guardrails only | Defence in depth; recurring guardrail costs (~USD 0.8k/month) |
| ADR-MSC-05 | Redact PII before the graph; LangSmith with hidden I/O or self-hosted | Send raw text to SaaS tracing | Less debuggability; compliance |
| ADR-MSC-06 | Bedrock KB / OpenSearch behind `KnowledgeBase` interface | Chroma in prod | Managed durability; interface keeps local dev |
| ADR-MSC-07 | Denial/appeal text from approved templates inserted by code | LLM-written legal text | Compliance control; less natural phrasing |
| ADR-MSC-08 | Smaller model for supervisor and critic (modelled -49% LLM cost) | One large model for all | Needs eval to show no quality loss |
| ADR-MSC-09 | Leakage canary in production | Test-only checks | Continuous assurance; synthetic canary members required |
| ADR-MSC-10 | Staged release: employee beta -> 10% -> 100% (representative-first as an option) | Big-bang | Longer timeline; lower risk |

## Consolidated risks
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-MSC-01 | Hallucinated benefit/denial | Critic, citations, record-quoted fields, eval gate | AI Lead |
| R-MSC-02 | Cross-member disclosure | Code authz, JWT identity, canary, red-team | Security |
| R-MSC-03 | PHI to provider/tracing | Redaction, BAA, hidden/self-hosted tracing | Privacy |
| R-MSC-04 | Bias/inequitable answers | Fairness evals, readability, tone review | Compliance |
| R-MSC-05 | Injection/jailbreak (known gaps) | Bedrock Guardrails, tool authz, red-team growth | Security |
| R-MSC-06 | Plan-year/model drift | Versioned docs, regression set, triggers | AI Lead |
| R-MSC-07 | Non-compliant wording | Templates, Compliance sign-off | Compliance |
| R-MSC-08 | Lock-in | Provider factory, KB interface, portable container | Architect |
| R-MSC-09 | Latency/quotas | Hosted model, smaller models, quota request | DevOps |
| R-MSC-10 | Member cannot reach a human | Persistent human option, SLA | Product Owner |
| R-MSC-11 | Cost per conversation exceeds target | Model mix, caching, alerts | DevOps |
| R-MSC-12 | Compliance review delays | Early templates and weekly reviews | Product Owner |
| R-MSC-13 | AgentCore HIPAA eligibility unclear | Fargate fallback path ready | Architect |

## Executive summary
**What:** a member-facing assistant that answers benefit questions with citations, explains claim denials from the member's own claim record plus policy, remembers the conversation, blocks injection, redacts PII, never shows another member's claim, and hands off to a person instead of guessing.
**Why:** more self-service resolution for repetitive questions and shorter handle time for representatives; pilot targets, not prototype results.
**Prototype:** 74 tests (69 pass, 5 documented guardrail gaps); local golden run: intent 0.947, retrieval hit 0.929, guardrail accuracy 1.0, leakage-free 1.0, keyword recall 0.639 (**below the 0.75 gate on the 3B local model**); red-team 27/27 must-pass; latency p50 ~27 s on CPU (synthetic data). Gaps: JWT identity, durable memory, Bedrock Guardrails evidence, claims API, handoff.
**Plan:** 9 months, 11.5 FTE peak, AWS (Bedrock + Guardrails, AgentCore Runtime or Fargate, KB, DynamoDB), CIAM JWT, compliance workstream, employee beta then staged rollout.
**Cost (ESTIMATE):** build ~USD 1.22M people plus 20% contingency (~1.46M); 12-month TCO ~USD 1.91M; 3-year ~USD 4.20M; LLM list-price ~USD 14k/month (~USD 0.16 per conversation), ~USD 7k/month with the modelled model-mix optimisation.
**Decisions needed:** HIPAA eligibility of each service, claims API access, member-facing vs representative-first release, tracing approach, business-case baseline cost per contact.
**Top risks:** cross-member disclosure, hallucinated denial explanation, PHI exposure, cost per conversation.

## Open questions (consolidated)
Spanish and voice timing; breach workflow; transcript retention; CIAM claims; handoff vendor; real baseline cost per contact; whether to tokenise claim amounts before the LLM.
