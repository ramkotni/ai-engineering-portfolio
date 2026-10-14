# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-CBR-001 | F | Five-section structured briefing per condition with numbered sources | Must |
| REQ-CBR-002 | F | Citation backfill or *unattributed* label; truncation handling; disclaimer | Must |
| REQ-CBR-003 | F | Counts, phases and rankings computed from the registry | Must |
| REQ-CBR-004 | F | Layout-aware PDF extraction (header/footer removal, column order, footnotes) | Must |
| REQ-CBR-005 | F | Cross-page table merge; figures extracted, captioned, verified, indexed | Must |
| REQ-CBR-006 | F | Follow-up Q&A with citations; "not covered" behaviour | Must |
| REQ-CBR-007 | F | Live ClinicalTrials.gov mode with date/NCT attribution and graceful degradation | Should |
| REQ-CBR-008 | F | Clearance enforced before retrieval and on documents/extraction/images endpoints | Must |
| REQ-CBR-009 | F | Refuse patient-specific advice; allow strategy questions mentioning doses | Must |
| REQ-CBR-010 | F | Number and ID grounding; injection and PHI guardrails; second-person language flag | Must |
| REQ-CBR-011 | F | Briefing cache with invalidation | Should |
| REQ-CBR-012 | F | Content rights register gating ingestion; quote limits | Must |
| REQ-CBR-013 | F | Clinical review sign-off recorded per briefing version | Must |
| REQ-CBR-014 | F | SSO with group-to-role mapping, default deny | Must |
| REQ-CBR-015 | F | Audit log of every request | Must |
| REQ-CBR-016 | NF | CI eval gate (extraction, retrieval, access, guardrails) | Must |
| REQ-CBR-017 | NF | 99.5% availability; canary + rollback; degraded facts-only mode | Must |
| REQ-CBR-018 | F | Feedback and error flags to content steward | Could |
| REQ-CBR-019 | NF | Briefing p95 <= 60 s (uncached); 8 concurrent | Must |
| REQ-CBR-020 | NF | TLS 1.2+, KMS, secrets manager, outbound allow-list | Must |
| REQ-CBR-021 | NF | WCAG 2.1 AA | Should |
| REQ-CBR-022 | NF | LLM spend alerting | Could |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 03 | graph, writer, verify | eval, E2E |
| 002 | 01 | 02 | verify | unit |
| 003 | 02 | 04, 05 | pipeline agent, trials.py | unit |
| 004 | 03 | 06 | loaders.py (PDF) | extraction contract |
| 005 | 03 | 07, 08, 09, 10, 41 | loaders.py, vision.py, chunking.py | extraction contract |
| 006 | 04 | 11, 12 | retrieval, Q&A path | eval |
| 007 | 05 | 13, 14, 15 | trials.py | integration, contract |
| 008 | 06 | 16, 17 | rbac.py, retrieval filters | security gate |
| 009 | 07 | 18, 19 | guardrails.py | red team |
| 010 | 08 | 20, 21, 22, 23 | guardrails.py, verify | red team |
| 011 | 09 | 24, 25 | cache | integration |
| 012 | 10 | 26, 27 | rights register, ingest | integration |
| 013 | 11 | 28, 44 | review service | integration, clinical |
| 014 | 12 | 29 | ALB OIDC, rbac | E2E |
| 015 | 12 | 30 | observability | integration |
| 016 | 13 | 31, 39-42 | eval/ | CI gate |
| 017 | 14 | 32, 38 | IaC, ECS | CD, DR |
| 018 | 15 | 33 | `/feedback` | API |
| 019 | NFR-1/2 | 34, 35, 36 | stack | load |
| 020 | NFR-4 | ZAP | infra | scans |
| 021 | NFR-5 | 37 | UI | staging |
| 022 | NFR-6 | 45 (to add) | monitoring | staging |
(UAT TC-CBR-43 traces to REQ-CBR-001, 006.)

## ADRs
| ID | Decision | Rejected | Consequence |
|---|---|---|---|
| ADR-CBR-01 | Fixed graph: four deterministic section agents in parallel + one writer call | ReAct multi-turn loop; one LLM call per section | Predictable, testable, cheaper; less flexible for novel briefing types |
| ADR-CBR-02 | Evidence and numbers computed in code; LLM writes prose; code verifies | LLM computes counts | Exactness; some stylistic stiffness |
| ADR-CBR-03 | Custom layout-aware extraction (pdfplumber + PyMuPDF) with extraction checks | Generic PDF-to-text; Textract-only | Handles columns, cross-page tables, figures; needs acceptance set on real layouts; Textract kept as scanned-PDF fallback |
| ADR-CBR-04 | Figures captioned by a vision model and verified, as their own chunks | Ignore figures; OCR only | Facts in figures retrievable; verification flag required |
| ADR-CBR-05 | Hybrid retrieval with BM25 | Vector only (F1 0.866 vs 0.924 on the prototype set) | Exact drug names, trial IDs, table labels retrieved |
| ADR-CBR-06 | Clearance and condition filters before ranking | Post-filtering | No internal text in public prompts |
| ADR-CBR-07 | Rights register gates ingestion | Ingest everything available | Slower onboarding of sources; legal safety |
| ADR-CBR-08 | Clinical reviewer sign-off per briefing version | Trust model output | Review effort; accountable clinical content |
| ADR-CBR-09 | OpenSearch + Bedrock on ECS Fargate | Chroma server, GPU hosting, Lambda | Managed hybrid search; per-month base cost |

## Consolidated risks
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-CBR-01 | Hallucinated facts | Deterministic evidence, grounding, review | AI Lead |
| R-CBR-02 | Misread tables/figures | Extraction checks, caption verification, extraction viewer | AI Lead |
| R-CBR-03 | Licence breach | Rights register, quote limits, Legal gate | Legal |
| R-CBR-04 | Internal leakage to consultants | Clearance before retrieval, probe in prod | Security |
| R-CBR-05 | Sponsor/coverage bias | Coverage reporting, classification audit | Product Owner |
| R-CBR-06 | Stale content | Refresh schedule, version in briefing, cache invalidation | Content steward |
| R-CBR-07 | Model/provider drift | Pinned models, regression set | AI Lead |
| R-CBR-08 | Misuse as clinical advice | Refusals, disclaimer, role limits, reviewer | Clinical Advisor |
| R-CBR-09 | Lock-in | Config switch | Architect |
| R-CBR-10 | Latency | Hosted model, cache | DevOps |
| R-CBR-11 | Real PDFs break extraction | 30-document acceptance set, fallback | AI Lead |
| R-CBR-12 | Live API changes | Contract tests, cached snapshots | Backend |

## Executive summary
**What:** an assistant that produces a structured, cited briefing on a medical condition (standard of care, emerging treatments, key companies and institutions, strategic considerations) from complex PDFs, internal documents and registries, with optional live ClinicalTrials.gov data and follow-up Q&A, within clearance and licence limits.
**Why:** days of assembly become minutes of drafting plus review; consistent format; computed counts. Pilot targets, not prototype results.
**Prototype:** 37 tests; extraction 8/8 (columns, cross-page table, figures, footnotes); retrieval hit@6 1.0, MRR 0.917; 0 internal chunks to the public role; guardrails 1.0/1.0; registry analytics 6/6; RAGAS hybrid precision 0.958 / recall 0.892 (synthetic data). Gaps: briefing took ~492-600 s on CPU; faithfulness unmeasured with a strong judge; licences and real layouts untested.
**Plan:** 5 months, 6.65 FTE peak, AWS (Bedrock, OpenSearch, ECS), SSO, rights register, clinical review workflow, CI eval gate, pilot on one service line.
**Cost (ESTIMATE):** build ~USD 0.35M people plus 15% contingency (~0.40M); 12-month TCO ~USD 0.64M; 3-year ~USD 1.36M; infrastructure ~USD 1.2k/month; LLM ~USD 23/month; licence fees excluded.
**Decisions needed:** licensing decisions per source, clinical reviewer of record, export formats, outbound access to the registry API.
**Top risks:** licence breach, extraction errors on real PDFs, hallucinated facts.

## Open questions (consolidated)
Licensed sources; reviewer SLA; export formats; scanned documents; EU registries (CTIS); data-retention for briefings.
