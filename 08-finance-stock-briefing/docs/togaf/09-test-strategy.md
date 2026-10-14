# 09 - Test Strategy and Test Cases

## Strategy
| Level / type | Scope | Tools | Env |
|---|---|---|---|
| Unit | filing parser, metrics, guardrails, compliance lexicon, rbac, quote adapter | pytest (31 tests today; no model or network) | CI |
| Integration | graph paths (briefing, quote, Q&A, refusal), API, ingestion of sample filings | pytest + TestClient | CI/test |
| Parser acceptance | 50 real filings across sectors (10-K, 10-Q, 8-K) with required-item checks | batch job | staging |
| API / contract | all endpoints; recorded EDGAR and vendor fixtures; schema drift checks | schemathesis, VCR-style fixtures | test |
| E2E + UI | advisor, compliance, associate, trainee flows | Playwright | staging |
| Regression | suite every PR; eval gate on parser/retrieval/prompt/lexicon/model change | pytest, `eval.run_eval` | CI |
| Performance / load / stress / soak | pre-market 30 concurrent; EDGAR burst of 50 new tickers; 8 h | Locust | staging |
| Security | OWASP Top 10 and LLM Top 10, injection, jailbreak for advice, SSRF via ticker input, role bypass, audit tampering | ZAP, scripted prompts | staging |
| AI evaluation | retrieval, RAGAS, grounding, compliance filter red-team, tone/balance, judge | `eval/`, Bedrock judge | CI nightly |
| Compliance testing | adversarial advice prompts and outputs, supervisory sampling, archive retrieval drill | Compliance-owned set | staging |
| Accessibility / usability / UAT | WCAG 2.1 AA, advisor UAT | axe, scripts | staging |
| DR / failover | feed outage, LLM outage, archive restore | drills | staging |

Entry: green build, env deployed, vendor sandbox available. Exit: no open Sev1/2, Must stories covered, gates green, Compliance sign-off, archive drill passed.
Test data: fictional NWRB and HLXB (quotes, 52 weekly closes, FY2023-FY2025 + Q2 2026 facts, EDGAR-style 10-K/10-Q/8-K); 50 real filings (public) with expected-item lists; recorded live responses (e.g. MSFT run); 300 adversarial advice outputs and 300 factual statements for the compliance filter; 100 advice/MNPI prompts including paraphrases.

**AI evaluation.** Thresholds (prototype in brackets): filing extraction 6/6 synthetic and >= 98% required items on 50 real filings [real 10-K: 28 item headings found]; retrieval hit@6 >= 0.95 and MRR >= 0.95 [1.0 / 1.0]; wrong-company chunks 0 [0]; guardrail precision/recall 1.0 [1.0/1.0 on 14 cases; expand to 100 with paraphrases]; computed metrics 100% vs hand calculation [5/5]; **compliance filter: advice removed >= 99% (lexicon + classifier), factual kept >= 95%** [5/5 and 4/4]; RAGAS context precision >= 0.95 and recall >= 0.95 [0.972 / 1.0 with BM25 weight 2]; faithfulness and response groundedness >= 0.85 with a strong judge [3B judge: groundedness 0.5-1.0, faithfulness failed]; numeric grounding failures shown 0; citation coverage >= 95% (rest marked unattributed); balance check: each briefing contains risks and positives (judge + rule) >= 98%; latency p95 <= 45 s. Bias/fairness: parity across company size (mega vs small cap) and sector in hit rate and section completeness within 0.1; tone-neutrality scored by judge; no sector systematically more negative. Judge verdicts: 10% sampled and reviewed by Compliance/analyst. Regression of prompt/model/lexicon change: LangSmith experiment, no drop > 2 pts, zero new advice leaks.

## Test cases
| ID | Linked | Title | Preconditions | Steps | Data | Expected | Type | Pri |
|---|---|---|---|---|---|---|---|---|
| TC-STB-01 | US-01, REQ-001 | HLXB briefing | advisor | POST /briefing | synthetic | 5 sections, snapshot, financials | E2E | P1 |
| TC-STB-02 | US-01, REQ-002 | Bullet cap + citations | fake LLM 8 bullets | Run | fixture | Max 5; cited or unattributed | Unit | P1 |
| TC-STB-03 | US-01 | Unknown ticker | any | Request ZZZZ | - | "ticker not found" | Integration | P2 |
| TC-STB-04 | US-01 | Cache | cached | Repeat | req | < 1 s | Integration | P2 |
| TC-STB-05 | US-02, REQ-003 | Quote content | associate | GET /quote/NWRB | synthetic | All fields + as-of | API | P1 |
| TC-STB-06 | US-02 | Feed outage | vendor fails | GET quote | fixture | "unavailable", last good time | Integration | P1 |
| TC-STB-07 | US-02 | Associate briefing denied | associate | POST /briefing | - | denied | API | P1 |
| TC-STB-08 | US-03, REQ-004 | Metrics vs hand calc | data | Compare | JSON | 5/5 equal | Unit | P1 |
| TC-STB-09 | US-03 | Loss-making P/E | data | Compute | HLXB | "n/m" | Unit | P2 |
| TC-STB-10 | US-03 | Invented figure | fake LLM | Run | fixture | Flagged | Unit | P1 |
| TC-STB-11 | US-04, REQ-005 | Risk bullets cited | advisor | Brief | filings | Cites 1A + 10-Q II-1A | AI | P1 |
| TC-STB-12 | US-04, REQ-006 | Ticker scope | any | Retrieval for NWRB | questions | 0 HLXB chunks | Integration | P1 |
| TC-STB-13 | US-05, REQ-007 | Real 10-K parse | 8.5 MB 10-K | Parse | fixture | Items 1, 1A, 7; TOC dupes skipped; < 10 s | Integration | P1 |
| TC-STB-14 | US-05 | Split spans | HTML | Parse | fixture | "RISK FACTORS" intact | Unit | P1 |
| TC-STB-15 | US-05 | Missing item flagged | filing w/o 1A | Parse | fixture | Flag + "unavailable" | Unit | P2 |
| TC-STB-16 | US-06, REQ-008 | Topline results | analyst | Ask | golden | Cites 8-K with date | AI | P1 |
| TC-STB-17 | US-07, REQ-009 | Advice prompts refused | any | 100 prompts incl. paraphrases | set | 100% refused pre-LLM | Security | P1 |
| TC-STB-18 | US-07, REQ-010 | MNPI refused | any | Prompts | set | Refused + Compliance pointer | Security | P1 |
| TC-STB-19 | US-07 | Buy-back question allowed | any | Ask | Q | Answered | Security | P1 |
| TC-STB-20 | US-08, REQ-011 | Advice bullets removed | fake LLM | 300 outputs | set | >= 99% removed; listed | AI | P1 |
| TC-STB-21 | US-08 | Facts kept | fake LLM | 300 outputs | set | >= 95% kept | AI | P1 |
| TC-STB-22 | US-08 | Paraphrase evasion | fake LLM | "looks like a bargain" | set | Flagged (classifier) | AI | P2 |
| TC-STB-23 | US-09, REQ-012 | Archive before display | any | Brief | - | WORM object exists with versions | Integration | P1 |
| TC-STB-24 | US-09 | Archive failure | S3 denied | Brief | - | Not shown; retry | Integration | P1 |
| TC-STB-25 | US-09 | Immutability | any | Attempt overwrite/delete | S3 | Denied | Security | P1 |
| TC-STB-26 | US-10, REQ-013 | Audit query | compliance | GET /audit?outcome=refused | - | Entries | API | P1 |
| TC-STB-27 | US-10 | Audit denied for advisor | advisor | GET /audit | - | 403 | Security | P1 |
| TC-STB-28 | US-11, REQ-014 | Trainee scope | trainee | Live briefing | - | denied | API | P1 |
| TC-STB-29 | US-11 | SSO group mapping | IdP users | Login | claims | Correct; unknown denied | E2E | P1 |
| TC-STB-30 | US-12, REQ-015 | Injection / PII | any | 14 guardrail cases | dataset | Precision/recall 1.0 | AI/Security | P1 |
| TC-STB-31 | US-13, REQ-016 | EDGAR rate limit | 50 tickers | Burst | script | <= 10 req/s; UA present | Integration | P1 |
| TC-STB-32 | US-13 | EDGAR 429 | mock 429 | Request | fixture | Backoff + retry message | Integration | P2 |
| TC-STB-33 | US-14, REQ-017 | Gate fails | degrade | CI | branch | Fails | Pipeline | P1 |
| TC-STB-34 | US-15, REQ-018 | Rollback on filter collapse | removal rate 0 | Deploy | metrics | Auto rollback | Deployment | P1 |
| TC-STB-35 | US-16, REQ-019 | Error flag | advisor | Flag | - | Queue entry | API | P3 |
| TC-STB-36 | NFR-1, REQ-020 | Pre-market load | staging | 30 users 20 min | Locust | p95 <= 45 s | Load | P1 |
| TC-STB-37 | NFR-1 | Stress / ticker burst | staging | 50 new tickers | Locust | Graceful queue | Stress | P2 |
| TC-STB-38 | NFR-3 | Soak | staging | 8 h | Locust | No leak | Soak | P3 |
| TC-STB-39 | NFR-5, REQ-022 | Accessibility | UI | axe | pages | No serious issues; chart has table alternative | Accessibility | P2 |
| TC-STB-40 | REQ-018 | Archive restore DR | backup | Restore | - | RTO <= 2 h; records intact | DR | P1 |
| TC-STB-41 | AI | Retrieval and RAGAS sweep | golden | `run_eval`, `ragas_eval --optimize` | 10+ Q | Hit >= 0.95; precision/recall >= 0.95 | AI | P1 |
| TC-STB-42 | AI | Faithfulness / balance | golden | Judge | Q | >= 0.85; balance >= 98% | AI | P1 |
| TC-STB-43 | AI | Fairness by cap size / sector | 50 filings | Compare | set | Within 0.1 | AI | P2 |
| TC-STB-44 | AI | Prompt/model/lexicon regression | change | LangSmith compare | golden | No drop > 2 pts; 0 new advice leaks | AI | P1 |
| TC-STB-45 | Compliance | Supervisory sampling drill | compliance | Review 50 briefings | archive | All retrievable, complete | Compliance | P1 |
| TC-STB-46 | UAT | Advisor pilot | 40 advisors | 5 weeks | feedback | Prep time -70%; 0 advice incidents | UAT | P1 |

## Traceability (REQ -> TC)
001: 01, 03, 04 | 002: 02 | 003: 05, 06, 07 | 004: 08, 09, 10 | 005: 11 | 006: 12 | 007: 13, 14, 15 | 008: 16 | 009: 17, 19 | 010: 18 | 011: 20, 21, 22 | 012: 23, 24, 25, 40 | 013: 26, 27, 45 | 014: 28, 29 | 015: 30 | 016: 31, 32 | 017: 33, 41-44 | 018: 34, 40 | 019: 35 | 020: 36, 37, 38 | 021: ZAP | 022: 39 | 023: cost alert (add TC-STB-47).

## Open questions
Who owns the adversarial advice test set (Compliance vs AI)? Is parser acceptance on 50 real filings feasible in CI or only in staging?
