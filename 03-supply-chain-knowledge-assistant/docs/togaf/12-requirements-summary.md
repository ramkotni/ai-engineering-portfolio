# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-SCK-001 | F | Cited question answering across formats | Must |
| REQ-SCK-002 | F | Figure content searchable via captioned image chunks, with source image shown | Must |
| REQ-SCK-003 | F | Summaries in brief, detailed, executive styles | Must |
| REQ-SCK-004 | F | Semantic + keyword search, exact `LOT-` lookup | Must |
| REQ-SCK-005 | F | Classification (clearance) enforced before retrieval | Must |
| REQ-SCK-006 | F | Same clearance on `/documents` and `/images/{id}`; unlabelled = confidential | Must |
| REQ-SCK-007 | F | Refuse disposition commands | Must |
| REQ-SCK-008 | F | Refuse medical/dosing advice | Must |
| REQ-SCK-009 | F | ID and number grounding | Must |
| REQ-SCK-010 | F | DMS sync with revision, effective/superseded handling | Must |
| REQ-SCK-011 | F | Quarantine documents lacking metadata; caption cache by hash | Must |
| REQ-SCK-012 | F | Faithful extraction of tables and figures | Must |
| REQ-SCK-013 | F | SSO and partner federation, default deny | Must |
| REQ-SCK-014 | F | Immutable audit trail | Must |
| REQ-SCK-015 | F | Feedback and missing-content flag | Should |
| REQ-SCK-016 | NF | CI eval gate | Must |
| REQ-SCK-017 | NF | Validated release with traceability and evidence | Must |
| REQ-SCK-018 | NF | 99.5% availability; canary + rollback; RTO 4 h / RPO 24 h | Must |
| REQ-SCK-019 | NF | p95 `/ask` <= 20 s; 15 concurrent | Must |
| REQ-SCK-020 | NF | TLS 1.2+, KMS, secrets manager | Must |
| REQ-SCK-021 | NF | WCAG 2.1 AA | Should |
| REQ-SCK-022 | NF | LLM spend alerting | Should |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 02 | retrieve, generate, verify | unit, eval |
| 002 | 02 | 04, 05 | image pipeline, retriever | eval gate |
| 003 | 03 | 06, 07 | summarize prompt | integration |
| 004 | 04 | 08, 09 | retriever, record chunks | unit |
| 005 | 05 | 10, 11 | rbac, retrieve filter | security gate |
| 006 | 05 | 12, 13 | `/documents`, `/images` | API test |
| 007 | 06 | 14 | guard_input | red team |
| 008 | 06 | 15, 16 | guard_input | red team |
| 009 | 01 | 03 | verify | unit |
| 010 | 07 | 17 | ingestion | integration |
| 011 | 07 | 18, 19 | ingestion, caption cache | integration |
| 012 | 08 | 20, 21 | loaders, chunker | unit |
| 013 | 09 | 22 | ALB OIDC, rbac | E2E |
| 014 | 10 | 23 | audit + S3 lock | security |
| 015 | 11 | 24 | `/feedback` | API |
| 016 | 12 | 25, 33-37 | eval/ | CI gate |
| 017 | 13 | 26 | CD gate | CD |
| 018 | 14 | 27, 32 | IaC, ECS | CD, DR |
| 019 | NFR-1/2 | 28, 29, 30 | stack | load |
| 020 | NFR-4 | ZAP | infra | scans |
| 021 | NFR-5 | 31 | UI | staging |
| 022 | NFR-6 | 41 (to add) | monitoring | staging |

## ADRs
| ID | Decision | Rejected | Consequence |
|---|---|---|---|
| ADR-SCK-01 | Single deterministic workflow | Multi-agent | Fewer LLM calls; less flexible routing |
| ADR-SCK-02 | Clearance filter before ranking, in code, on every endpoint | Post-filter results; DMS ACL only | No restricted text in prompts; must maintain classification metadata |
| ADR-SCK-03 | Figures as captioned `image` chunks with source image | Ignore figures; OCR only | Facts in figures searchable; captions can err -> labelled, verified |
| ADR-SCK-04 | Bedrock text + vision models behind `llm.py` | Local gemma3:4b in prod (~170 s/figure on CPU) | Speed/quality; vendor dependency mitigated |
| ADR-SCK-05 | OpenSearch managed hybrid | Kendra, Chroma server | Control over filter-first retrieval |
| ADR-SCK-06 | Read-only toward DMS | Write-back (deviation drafts) | Lower risk; Phase 2 may revisit with human approval |
| ADR-SCK-07 | Fail closed on missing classification | Default internal | Possible exceptions backlog; no leak |
| ADR-SCK-08 | Risk-based validation with automated evidence | Manual scripts | Faster releases; needs QA buy-in |
| ADR-SCK-09 | Retrieval k=6 on CPU, k=10 on hosted models | k=10 everywhere | Latency vs recall (RAGAS sweep +0.018 F1) |

## Consolidated risks
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-SCK-01 | Mis-cited or hallucinated procedure | Grounding, citations, DMS verify reminder | AI Lead |
| R-SCK-02 | Wrong figure caption | Label, source image, caption eval, human review of critical figures | AI Lead / QA |
| R-SCK-03 | Partner sees confidential content | Filter-first, endpoint checks, alarms with auto rollback | Security |
| R-SCK-04 | Format/length bias | Source-type eval | AI Lead |
| R-SCK-05 | Stale or superseded content | Event sync, effective filters, freshness SLO | Data Eng |
| R-SCK-06 | Validation delays | Early CSV lead, automated evidence | QA |
| R-SCK-07 | Lock-in | `llm.py` | Architect |
| R-SCK-08 | Poisoned document / injection | Data/instruction separation, TC-38 | Security |
| R-SCK-09 | Classification metadata quality | Fail closed, steward, sampling | Content steward |
| R-SCK-10 | Cost of captioning/LLM | Cache, alerts (one-time captioning ~USD 63) | DevOps |

## Executive summary
**What:** a cited question-answering, summarisation and search assistant over controlled supply-chain documents in five formats, including facts inside figures, with classification-based access so partners only see public content.
**Why:** faster answers during excursions and inspections; one search across formats; no leakage. Pilot targets, not prototype results.
**Prototype:** 18 tests; retrieval hit@6 and MRR 1.0 on 10 questions; image chunks retrieved for 100% of figure questions; 0 restricted chunks to the partner role; guardrail precision/recall 1.0 on 11 cases (synthetic data). Gaps: CPU vision captions took ~170 s per figure; RAGAS faithfulness needs a stronger judge.
**Plan:** 8 months, 9.25 FTE peak, AWS (Bedrock, OpenSearch, ECS), SSO + partner federation, DMS sync, risk-based validation, CI eval gate.
**Cost (ESTIMATE):** build/validate ~USD 0.81M plus 20% contingency; 12-month TCO ~USD 1.23M; 3-year ~USD 2.31M; LLM ~USD 200/month.
**Decisions needed:** GxP classification outcome, DMS API access, partner identity approach, validation approach.
**Top risks:** partner leakage, caption errors, stale content.

## Open questions (consolidated)
GxP applicability; DMS metadata/API; partner IdP; audit retention; superseded-version search; scanned PDFs (OCR); multilingual.
