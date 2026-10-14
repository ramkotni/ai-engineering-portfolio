# 09 - Test Strategy and Test Cases

## Strategy
| Level / type | Scope | Tools | Env |
|---|---|---|---|
| Unit | loaders, table merge, reading order, chunking, analytics, guardrails, rbac, trials parser | pytest (37 tests today; fake LLM and keyword retriever) | CI |
| Integration | graph paths (briefing, follow-up, refusal), API, ingestion of sample files | pytest + TestClient | CI/test |
| Extraction contract | 8 named checks per complex PDF (header/footer, columns, merged table, all rows, figures, footnotes, Word image, captions) | `eval.run_eval` | CI |
| API / contract | `/briefing`, `/ask`, `/conditions`, `/documents`, `/extraction`, `/images/{id}` | schemathesis | test |
| E2E + UI | role flows | Playwright | staging |
| Regression | suite every PR; eval gate on extraction/retrieval/prompt/model change | pytest, `eval.run_eval` | CI |
| Performance / load / stress / soak | 8 concurrent briefings; ingestion of 500 documents | Locust, batch timer | staging |
| Security | OWASP Top 10 and LLM Top 10, injection (incl. poisoned PDF), clearance bypass, SSRF in live mode, DoS by large PDFs | ZAP, scripted prompts | staging |
| AI evaluation | retrieval, RAGAS, grounding, completeness, clinical review, judge | `eval/`, Bedrock judge | CI nightly |
| Accessibility / usability / UAT | WCAG 2.1 AA, analyst UAT | axe, scripts | staging |
| DR / failover | restore index from S3, LLM outage | drills | staging |

Entry: green build, env deployed, content loaded and rights cleared. Exit: no open Sev1/2, Must stories covered, gates green, clinical + legal sign-off.
Test data: 4 synthetic sources (public PDF with two columns, cross-page table, 2 figures; HTML; internal Word with chart; 26-row registry); expand to a 30-document real extraction set once licensed (layout variety, scans excluded); poisoned PDF with injected instruction; live API recorded fixtures.

**AI evaluation.** Thresholds (prototype in brackets): extraction checks 8/8 [8/8] on contract docs and >= 95% on the 30-document real set; retrieval hit@6 >= 0.95 [1.0] and MRR >= 0.90 [0.917] with hit rate >= 0.9 for every source type (table, continued-page table row, figure, two-column text, HTML, record, Word internal, footnote) [1.0 each]; internal chunks to public role = 0 [0]; guardrail precision/recall 1.0 [1.0/1.0 on 14 cases]; registry analytics 100% vs direct count [6/6]; RAGAS context precision >= 0.90 and recall >= 0.85 [0.958 / 0.892]; faithfulness and response groundedness >= 0.85 with a strong judge [3B judge failed: groundedness 0.0-1.0, faithfulness 0.333 / failed]; ungrounded numbers/IDs shown 0; section completeness 100%; unattributed bullets <= 5%; clinical-advisor rating >= 4/5 on 10 sampled briefings; briefing latency p95 <= 60 s. Bias/fairness: sponsor coverage report - top-ranked companies must not be excluded by registry artefacts (e.g. academic vs company classification checked on 50 sponsors); hit rate across document formats within 0.1. Judge verdicts: 10% sampled and reviewed by the clinical advisor/analyst. Regression of prompt/model change: LangSmith experiment, no drop > 2 pts.

## Test cases
| ID | Linked | Title | Preconditions | Steps | Data | Expected | Type | Pri |
|---|---|---|---|---|---|---|---|---|
| TC-CBR-01 | US-01, REQ-001 | HFrEF briefing | analyst | POST /briefing | synthetic | 5 sections, cited | E2E/AI | P1 |
| TC-CBR-02 | US-01, REQ-002 | Unattributed labelling | fake LLM omits citations | Run | fixture | Backfilled or *unattributed* | Unit | P1 |
| TC-CBR-03 | US-01 | Truncated bullet | token cap | Run | fixture | Trimmed + flag | Unit | P2 |
| TC-CBR-04 | US-02, REQ-003 | Counts vs registry | data | Compare | CSV | 6/6 equal | Unit | P1 |
| TC-CBR-05 | US-02 | Invented count | fake LLM | Run | fixture | Corrected/flagged | Unit | P1 |
| TC-CBR-06 | US-03, REQ-004 | Header/footer + columns | PDF | Extract | guideline PDF | Removed; left before right | Unit | P1 |
| TC-CBR-07 | US-03, REQ-005 | Cross-page table | PDF | Extract | guideline PDF | Merged, all rows | Unit | P1 |
| TC-CBR-08 | US-03 | Figure caption chunk | PDF | Extract+caption | figures | Chunks under section; image served | Integration | P1 |
| TC-CBR-09 | US-03 | Caption verification flag | seeded misread | Extract | fixture | Flagged | Unit | P1 |
| TC-CBR-10 | US-03 | Failed check quarantine | corrupted PDF | Ingest | file | Quarantined | Integration | P1 |
| TC-CBR-11 | US-04, REQ-006 | CRT-D from figure | analyst | Ask | golden | Cites figure chunk | AI | P1 |
| TC-CBR-12 | US-04 | Not covered | analyst | Ask off-topic | Q | Says not covered | Integration | P2 |
| TC-CBR-13 | US-05, REQ-007 | Live AF briefing | analyst | source live | recorded fixture | 40 studies, NCT IDs, date | Integration | P1 |
| TC-CBR-14 | US-05 | Executive live denied | executive | live | - | denied | API | P1 |
| TC-CBR-15 | US-05 | API outage | API down | live | - | Cache/warning | Integration | P2 |
| TC-CBR-16 | US-06, REQ-008 | Consultant no internal | consultant | Briefing + QA | Q | 0 internal chunks; strategy unavailable | Security | P1 |
| TC-CBR-17 | US-06 | Hidden internal docs | consultant | GET /extraction, /images | ids | Hidden / 403 | Security | P1 |
| TC-CBR-18 | US-07, REQ-009 | Patient advice refused | any | Ask | Q | Refused | Security | P1 |
| TC-CBR-19 | US-07 | Dose strategy question allowed | any | Ask | Q | Answered | Security | P1 |
| TC-CBR-20 | US-08, REQ-010 | Unknown NCT ID | fake LLM | Run | fixture | Removed/flagged | Unit | P1 |
| TC-CBR-21 | US-08 | Second-person language | fake LLM | Run | fixture | Flagged | Unit | P2 |
| TC-CBR-22 | US-08 | Injection + PHI | any | 14 guardrail cases | dataset | Precision/recall 1.0 | AI/Security | P1 |
| TC-CBR-23 | US-08 | Poisoned PDF | injected instruction | Ingest+brief | fixture | Not followed | Security (LLM01) | P1 |
| TC-CBR-24 | US-09, REQ-011 | Cache hit < 1 s | cached | Repeat | req | Instant; same content | Integration | P2 |
| TC-CBR-25 | US-09 | Invalidation on refresh | refresh | Repeat | req | New content | Integration | P1 |
| TC-CBR-26 | US-10, REQ-012 | Rights gate | doc w/o rights | Ingest | file | Rejected | Integration | P1 |
| TC-CBR-27 | US-10 | Quote limit | licence 150 words | Brief | doc | No quote above limit | Unit | P1 |
| TC-CBR-28 | US-11, REQ-013 | Review sign-off | advisor | Approve | briefing | Stored; superseded on regenerate | Integration | P1 |
| TC-CBR-29 | US-12, REQ-014 | Group to role | IdP users | Login | claims | Correct | E2E | P1 |
| TC-CBR-30 | US-12, REQ-015 | Audit | any | Request | - | Fields complete | Integration | P1 |
| TC-CBR-31 | US-13, REQ-016 | Gate fails | degrade | CI | branch | Fails | Pipeline | P1 |
| TC-CBR-32 | US-14, REQ-017 | Canary rollback | 500s | Deploy | - | Auto rollback | Deployment | P1 |
| TC-CBR-33 | US-15, REQ-018 | Error flag | analyst | Flag bullet | - | Steward queue item | API | P3 |
| TC-CBR-34 | NFR-1, REQ-019 | Load | staging | 8 concurrent 15 min | Locust | p95 <= 60 s | Load | P1 |
| TC-CBR-35 | NFR-1 | Stress / large PDFs | staging | 100-page PDF; 20 concurrent | files | Graceful; limits enforced | Stress | P2 |
| TC-CBR-36 | NFR-3 | Soak | staging | 8 h | Locust | No leak | Soak | P3 |
| TC-CBR-37 | NFR-5, REQ-021 | Accessibility | UI | axe | pages | No serious issues | Accessibility | P2 |
| TC-CBR-38 | REQ-017 | DR + LLM outage | block LLM | Brief | req | Facts-only briefing/cached | DR | P1 |
| TC-CBR-39 | AI | Retrieval by source type | golden | `run_eval` | 12 Q | hit@6 >= 0.95; each type >= 0.9 | AI | P1 |
| TC-CBR-40 | AI | RAGAS and judge | golden | `ragas_eval --llm` | Q | Faith/ground >= 0.85 | AI | P1 |
| TC-CBR-41 | AI | Real-document extraction acceptance | 30 real PDFs | Extract | set | >= 95% checks | AI | P1 |
| TC-CBR-42 | AI | Sponsor classification and coverage | registry | Compare | 50 sponsors | >= 95% correct | AI | P2 |
| TC-CBR-43 | UAT | Analyst pilot | pilot | 10 briefings | team | Prep time -60%; rating >= 4/5 | UAT | P1 |
| TC-CBR-44 | Clinical | Advisor review | advisor | 10 sampled briefings | briefings | >= 4/5 accuracy, no unsafe claims | Clinical | P1 |

## Traceability (REQ -> TC)
001: 01, 03 | 002: 02 | 003: 04, 05 | 004: 06 | 005: 07, 08, 09, 10 | 006: 11, 12 | 007: 13, 14, 15 | 008: 16, 17 | 009: 18, 19 | 010: 20, 21, 22, 23 | 011: 24, 25 | 012: 26, 27 | 013: 28, 44 | 014: 29 | 015: 30 | 016: 31, 39-42 | 017: 32, 38 | 018: 33 | 019: 34, 35, 36 | 020: ZAP (incl. SSRF) | 021: 37 | 022: cost alert (add TC-CBR-45).

## Open questions
Where do the 30 real documents come from (licensing)? Who is the clinical reviewer of record for test sign-off?
