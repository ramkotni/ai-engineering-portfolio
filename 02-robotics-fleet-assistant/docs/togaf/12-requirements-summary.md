# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-FLT-001 | F | Diagnose robots: probable cause with event IDs and first action | Must |
| REQ-FLT-002 | F | Zone/event-type filtered navigation and Wi-Fi history | Must |
| REQ-FLT-003 | F | Battery degradation from 30-day least-squares slope vs policy | Must |
| REQ-FLT-004 | F | Risk-ranked predictive maintenance with reasons | Must |
| REQ-FLT-005 | F | Rebalancing proposals within a zone per BR-2 | Must |
| REQ-FLT-006 | F | Fleet status by zone | Should |
| REQ-FLT-007 | F | Daily fleet report with role-appropriate tone | Should |
| REQ-FLT-008 | F | Intent-level RBAC | Must |
| REQ-FLT-009 | F | Zone-scoped data in authorize, retrieval and analytics | Must |
| REQ-FLT-010 | F | Refuse safety-override and restricted-zone requests | Must |
| REQ-FLT-011 | F | ID and number grounding | Must |
| REQ-FLT-012 | F | Withhold unsafe output | Must |
| REQ-FLT-013 | F | Audit log for every request | Must |
| REQ-FLT-014 | F | Scheduled ingestion and freshness monitoring | Must |
| REQ-FLT-015 | F | SSO with role and zone claims | Must |
| REQ-FLT-016 | NF | 99.5% availability; canary + rollback; no impact on robot operation | Must |
| REQ-FLT-017 | NF | CI eval and safety gate | Must |
| REQ-FLT-018 | F | User feedback capture | Could |
| REQ-FLT-019 | NF | p95 <= 15 s at 12 concurrent | Must |
| REQ-FLT-020 | NF | TLS 1.2+, KMS, secrets manager | Must |
| REQ-FLT-021 | NF | WCAG 2.1 AA, tablet-usable | Should |
| REQ-FLT-022 | NF | LLM spend alerting | Should |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 02, 03 | Fleet Search, Diagnostics, guard_output | unit, eval |
| 002 | 02 | 04, 05 | Retriever, intent slots | eval |
| 003 | 03 | 06, 07 | analytics (battery) | unit |
| 004 | 04 | 08 | analytics (risk) | unit, eval |
| 005 | 05 | 09, 10 | Task Optimization | unit |
| 006 | 06 | 11 | Fleet Status | unit |
| 007 | 07 | 12 | Ops Summary | integration |
| 008 | 08 | 13, 15 | rbac, authorize | API |
| 009 | 08 | 14, 39 | retrieval + analytics filters | integration, security |
| 010 | 09 | 16, 17, 20 | guard_input | red team |
| 011 | 01, 09 | 02, 19 | guard_output | unit |
| 012 | 09 | 18 | guard_output | integration |
| 013 | 10 | 21 | observability | integration |
| 014 | 14 | 22, 23, 24 | ingestion jobs | integration, ops |
| 015 | 15 | 25 | ALB OIDC, rbac | E2E |
| 016 | 17 | 27, 33 | IaC, ECS | CD, DR |
| 017 | 16 | 26, 34, 35, 37 | eval/ | CI gate |
| 018 | 18 | 28 | /feedback | API |
| 019 | NFR-1 | 29, 30, 31 | stack | load |
| 020 | NFR-4 | ZAP | infra | scans |
| 021 | NFR-5 | 32 | UI | staging |
| 022 | NFR-6 | 40 (to add) | monitoring | staging |

## ADRs
| ID | Decision | Rejected | Consequence |
|---|---|---|---|
| ADR-FLT-01 | Fixed plan per intent; LLM only for intent + final narration | LLM-chosen tool loop | 2 calls per request; low cost; less flexibility |
| ADR-FLT-02 | Bedrock Claude behind `llm.py` | OpenAI, GPU self-hosting | In-region; abstraction limits lock-in |
| ADR-FLT-03 | Telemetry in Postgres/S3 Parquet, queried not embedded | Embedding time series, Timestream | Exact numbers; extra store |
| ADR-FLT-04 | Zone filter in three layers | Filter only at retrieval | Defence in depth; more tests |
| ADR-FLT-05 | Advisory only | Allow task reassignment API | Safer; approval flow deferred to Phase 2 and still human-executed |
| ADR-FLT-06 | OpenSearch hybrid search; k=10 | Chroma server; k=6 | Recall 1.0 vs 0.85 on golden set (RAGAS sweep) |
| ADR-FLT-07 | Policy thresholds in versioned config | Hard-coded | Auditable changes |
| ADR-FLT-08 | EHS owns safety-guardrail changes via CODEOWNERS | ARB only | Slower safety changes, clear accountability |

## Consolidated risks
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-FLT-01 | Wrong diagnosis | Grounding, feedback, senior review on fallback | AI Lead |
| R-FLT-02 | Unsafe advice | Dual-layer safety guardrails, EHS red-team | EHS |
| R-FLT-03 | Retrieval bias | Per-type eval | AI Lead |
| R-FLT-04 | Zone leak | Three-layer scope tests, TC-14/39 | Security |
| R-FLT-05 | Drift (new models/firmware) | Triggers in file 11 | AI Lead |
| R-FLT-06 | Stale telemetry | Freshness alerts, as-of display | Data Eng |
| R-FLT-07 | Lock-in | `llm.py` | Architect |
| R-FLT-08 | Overtrust of proposals | Reasons shown; approval step | Product Owner |
| R-FLT-09 | Site connectivity delay | File export fallback | Data Eng |
| R-FLT-10 | Cost overrun | Alerts, sizing review | DevOps |

## Executive summary
**What:** an advisory multi-agent assistant that diagnoses robot faults from incident history and the troubleshooting guide, finds degrading batteries, ranks maintenance risk, proposes workload moves and writes the daily fleet report, with zone-scoped access and safety guardrails.
**Why:** less unplanned downtime, batteries replaced before failure, balanced utilisation, faster handover. Pilot targets, not prototype results.
**Prototype:** 25 tests; guardrail precision/recall 1.0 on 14 cases; retrieval hit@k 1.0 and RAGAS recall 1.0 at k=10; planted patterns found 3/3 (synthetic data).
**Plan:** 6 months, 8.1 FTE peak, AWS (Bedrock, OpenSearch, RDS, ECS), SSO with zone claims, live connectors, CI eval and safety gate.
**Cost (ESTIMATE):** build ~USD 0.52M plus 15% contingency; 12-month TCO ~USD 0.85M; 3-year ~USD 1.66M; LLM usage ~USD 135/month.
**Decisions needed:** budget, site VPN, EHS participation, policy-threshold ownership.
**Top risks:** unsafe advice, wrong diagnosis, zone leakage.

## Open questions (consolidated)
Baselines; telemetry cadence; OT security policy on cloud; 24x7 support; threshold owner; contractor logging terms.
