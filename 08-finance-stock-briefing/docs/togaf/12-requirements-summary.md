# 12 - Requirements Management and Summary

## Requirements catalog
| ID | Type | Requirement | Priority |
|---|---|---|---|
| REQ-STB-001 | F | Briefing with snapshot, key financials and five cited sections per ticker | Must |
| REQ-STB-002 | F | Max 5 bullets per section; citations backfilled or marked unattributed | Must |
| REQ-STB-003 | F | Quote snapshot with as-of time/source; no silent stale data | Must |
| REQ-STB-004 | F | Financial metrics computed in code from XBRL/quote data | Must |
| REQ-STB-005 | F | Filings summary (risks, events) cited to sections and filing dates | Must |
| REQ-STB-006 | F | Retrieval scoped to the requested ticker | Must |
| REQ-STB-007 | F | Robust EDGAR HTML parsing (TOC dedupe, split spans, page furniture, tables) with required-item checks | Must |
| REQ-STB-008 | F | Follow-up Q&A on filings with citations | Must |
| REQ-STB-009 | F | Refuse investment advice requests | Must |
| REQ-STB-010 | F | Refuse MNPI requests | Must |
| REQ-STB-011 | F | Remove recommendation language from outputs and log removed statements | Must |
| REQ-STB-012 | F | Disclaimer, timestamps and immutable archive before display | Must |
| REQ-STB-013 | F | Compliance audit view (`/audit`) restricted to compliance role | Must |
| REQ-STB-014 | F | SSO role scoping (tasks, live data, style) | Must |
| REQ-STB-015 | F | Injection blocking and PII redaction | Must |
| REQ-STB-016 | NF | EDGAR fair access and vendor terms compliance | Must |
| REQ-STB-017 | NF | CI eval and compliance gate | Must |
| REQ-STB-018 | NF | 99.9% availability in trading hours; canary + rollback; DR RTO 2 h | Must |
| REQ-STB-019 | F | Feedback and error flagging | Could |
| REQ-STB-020 | NF | Briefing p95 <= 45 s uncached; 30 concurrent | Must |
| REQ-STB-021 | NF | TLS 1.2+, KMS, Object Lock, secrets manager | Must |
| REQ-STB-022 | NF | WCAG 2.1 AA | Should |
| REQ-STB-023 | NF | LLM and data-feed cost alerting | Should |

## Master traceability matrix
| REQ | US | TC | Component | Pipeline stage |
|---|---|---|---|---|
| 001 | 01 | 01, 03, 04 | graph, writer | E2E, eval |
| 002 | 01 | 02 | structure enforcement | unit |
| 003 | 02 | 05, 06, 07 | market.py, quote agent | API test |
| 004 | 03 | 08, 09, 10 | financials.py | unit |
| 005 | 04 | 11 | filings agent | eval gate |
| 006 | 04 | 12 | retrieval filters | integration |
| 007 | 05 | 13, 14, 15 | filings.py | parser acceptance |
| 008 | 06 | 16 | Q&A path | eval |
| 009 | 07 | 17, 19 | guard_input | red team |
| 010 | 07 | 18 | guard_input | red team |
| 011 | 08 | 20, 21, 22 | compliance review | compliance gate |
| 012 | 09 | 23, 24, 25, 40 | archive, writer | integration, DR |
| 013 | 10 | 26, 27, 45 | `/audit`, rbac | API, compliance |
| 014 | 11 | 28, 29 | rbac, OIDC | E2E |
| 015 | 12 | 30 | guardrails | red team |
| 016 | 13 | 31, 32 | edgar.py rate limiter | integration |
| 017 | 14 | 33, 41-44 | eval/ | CI gate |
| 018 | 15 | 34, 40 | IaC, ECS | CD, DR |
| 019 | 16 | 35 | `/feedback` | API |
| 020 | NFR-1/2 | 36, 37, 38 | stack | load |
| 021 | NFR-4 | ZAP, 25 | infra | scans |
| 022 | NFR-5 | 39 | UI | staging |
| 023 | NFR-6 | 47 (to add) | monitoring | staging |
(UAT TC-STB-46 traces to REQ-STB-001, 011.)

## ADRs
| ID | Decision | Rejected | Consequence |
|---|---|---|---|
| ADR-STB-01 | Fixed graph: three deterministic data agents in parallel + one writer call + compliance review | Autonomous research agent | Predictable, auditable, cheaper; less open-ended research |
| ADR-STB-02 | Numbers from XBRL/quotes computed in code; LLM never computes | LLM arithmetic | Exact figures; stricter prose |
| ADR-STB-03 | Licensed market-data vendor in production; Yahoo chart API prototype only | Yahoo or scraping in prod | Recurring data cost (~USD 1.5k/month ASSUMED); legal safety |
| ADR-STB-04 | Compliance-owned lexicon filter + refusal at input; classifier layer in Phase 2 | LLM-only self-policing | Deterministic, auditable; paraphrase gaps need classifier |
| ADR-STB-05 | Archive-before-display to WORM | Log after the fact | Latency + availability dependency on archive; regulatory defensibility |
| ADR-STB-06 | Ticker-scoped retrieval; BM25 weight 2 hybrid | Equal weights (F1 0.934) or vector only (0.930) | F1 0.986; exact terms prioritised |
| ADR-STB-07 | Own EDGAR parser + XBRL facts | Third-party summaries | Control and testability; maintenance burden |
| ADR-STB-08 | ECS Fargate + OpenSearch + Bedrock | GPU hosting, Lambda | Managed; fixed monthly base cost |
| ADR-STB-09 | Production deploys outside trading hours | Anytime | Slower releases; fewer disruptions |

## Consolidated risks
| ID | Risk | Mitigation | Owner |
|---|---|---|---|
| R-STB-01 | Hallucinated figure | Computed data, grounding, citations | AI Lead |
| R-STB-02 | Advice language slips through | Input refusals, filter, red-team, supervision | CCO |
| R-STB-03 | Unlicensed/unreliable data | Licensed vendor, timestamps | Legal |
| R-STB-04 | MNPI/client data in prompts | Refusal, redaction, no client data in MVP | Security |
| R-STB-05 | Coverage/tone bias by company size or sector | Balanced prompts, parity eval | AI Lead |
| R-STB-06 | Stale data | Timestamps, TTLs, freshness alerts | Data Eng |
| R-STB-07 | Drift (model, filing formats) | Pinned models, parser acceptance set, triggers | AI Lead |
| R-STB-08 | EDGAR throttling | Shared cache and limiter | Backend |
| R-STB-09 | Books-and-records failure | WORM archive-before-display, drill | Records Mgmt |
| R-STB-10 | Lock-in | Config switch, adapters | Architect |
| R-STB-11 | Regulatory change on AI communications | Compliance monitoring, flexible lexicon/controls | CCO |
| R-STB-12 | Pre-market overload | Pre-warm, autoscale, cache | DevOps |

## Executive summary
**What:** an assistant that gives financial advisors a briefing on a stock in minutes (quote snapshot, XBRL key financials, cited summary of the 10-K/10-Q/8-K) with a compliance filter that removes recommendation language and refuses advice and MNPI requests, plus an audit view for Compliance.
**Why:** 30-60 minutes of preparation becomes minutes, with consistent coverage and supervised output. Pilot targets, not prototype results.
**Prototype:** 31 tests; 6/6 filings extracted (real 8.5 MB 10-K parsed in 5.2 s); retrieval hit@6 and MRR 1.0, 0 cross-company chunks; guardrails 1.0/1.0; computed metrics 5/5; compliance filter 5/5 removed, 4/4 kept; RAGAS precision 0.972 / recall 1.0 after raising BM25 weight (synthetic data and a live MSFT check). Gaps: Yahoo quote source unlicensed for production, 232 s briefing on CPU, no archive/SSO, faithfulness unmeasured with a strong judge.
**Plan:** 5 months, 7.1 FTE peak, AWS (Bedrock, OpenSearch, ECS, S3 Object Lock), licensed market data, SSO, compliance package, pilot with 40 advisors.
**Cost (ESTIMATE):** build ~USD 0.39M people plus 20% contingency (~0.47M); 12-month TCO ~USD 0.77M; 3-year ~USD 1.60M; run cost ~USD 2.9k/month of which the data licence is an ASSUMED USD 1.5k; LLM ~USD 170/month.
**Decisions needed:** market-data vendor and budget, communications-rule classification of briefings, archive platform, classifier layer timing.
**Top risks:** advice-language leakage, unlicensed data, hallucinated figures.

## Open questions (consolidated)
Vendor; whether briefings may be shared with clients; archive platform; surveillance integration; transcripts; non-US coverage; classifier-based paraphrase detection.
