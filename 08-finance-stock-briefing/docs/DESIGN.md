# Stock Briefing Assistant - Design Document

Finance scenario: *"A wealth management firm wants a solution that helps advisors quickly get up to speed on a
stock - fetching current quote data and summarizing key information from recent SEC filings."* Portfolio prototype;
offline mode uses two fictional companies, live mode uses Yahoo Finance quotes and SEC EDGAR. Companion:
[README](../README.md), [pitch slide](Stock_Briefing_Pitch.pptx).

## 1. Problem, users and goals
Before a client conversation an advisor needs, in a few minutes: where the stock trades, how the business is doing
and what could go wrong. Today that means a quote screen plus skimming a 100-page 10-K, the latest 10-Q and recent
8-Ks - which advisors rarely have time for - and the firm must make sure nothing they say sounds like an
unsanctioned recommendation.

**Users:** financial advisors, research analysts, compliance officers, client-service associates (quotes only) and
advisor trainees (synthetic demo companies only) - see section 7.

| Goal | Design response |
|---|---|
| One page per stock in minutes | Fixed briefing: snapshot, key financials, business, recent performance, key risks, recent events, what to watch |
| Current market data | Quote agent: Yahoo Finance chart API (live) or synthetic snapshot; derived metrics computed in code |
| Trustworthy numbers | Financials from XBRL structured data, never read from prose by the LLM; every number in the text checked against the evidence |
| The right filing sections | EDGAR HTML parser that finds Items 1, 1A, 7 (10-K), Part I Item 2 and Part II Item 1A (10-Q) and 8-Ks |
| No advice, no MNPI | Input guardrails + a compliance review that removes recommendation language from the output |
| Supervision | Audit log readable by compliance; LangSmith traces |

## 2. Architecture
```
Ticker / name (API :8008 / Streamlit :8508 / CLI)
  -> LangGraph: guard_input -> resolve_company (synthetic catalogue | SEC ticker list) -> authorize
       -> prepare_filings (live: fetch + parse + index latest 10-K, 10-Q, two 8-Ks once, cached)
       -> [quote_agent | financials_agent | filings_agent]   (parallel)
       -> write_briefing (1 LLM call, numbered evidence) -> compliance_review -> briefing JSON + Markdown
  -> quote-only path for client-service associates; follow-up questions: retrieve (ticker filter) -> answer -> check
Data: Yahoo Finance chart API | SEC EDGAR submissions, filing documents, XBRL company facts | synthetic JSON + HTML
Index: EDGAR HTML -> sections -> structure-aware chunks -> nomic-embed-text -> ChromaDB (+ BM25, weighted RRF)
Monitoring: LangSmith, /metrics, audit log (GET /audit for compliance)
```

### Why this agent design
Three **data agents run in parallel** because they use different tools and none needs the LLM: the quote agent calls
a market-data API and computes change, 52-week position, 1-year return, market cap and P/E; the financials agent
reads XBRL facts and computes growth and margins; the filings agent retrieves chunks per briefing section with
filters (`ticker` + section group: business / mdna / risks / events). A **single writer call** narrates; a
deterministic **compliance review** follows. An open-ended tool-calling agent was rejected: the steps are the same
for every stock, and a fixed graph is cheaper, testable and auditable - which compliance needs.

## 3. Extraction - SEC filings
Filings are EDGAR HTML (inline XBRL), often several MB. `stockbrief/filings.py` handles the same structure in the
synthetic filings and in real ones (tested on an 8.5 MB 10-K: 5.2 s, 1,274 blocks, 28 item headings found, 5
table-of-contents / duplicate headings skipped, 33 page-furniture blocks removed, Items 1 / 1A / 7 extracted).

| Problem in real filings | Technique |
|---|---|
| Hidden XBRL header, scripts, `display:none` blocks | removed before parsing; lxml parser |
| Words split across styled spans ("RIS" + "K FACTORS") | text of a block joined without separators, then whitespace normalised |
| Table of contents repeats every Item heading | for each item, the occurrence followed by the longest section wins |
| Running "Item 1A" page headers, "Table of Contents" back-links, page numbers | dropped as noise (bare item numbers without a title are never headings) |
| 10-Q items repeat across Part I and Part II | keys qualified by part: `I-2` (MD&A), `II-1A` (risk-factor updates) |
| Financial tables: "$" in its own cell, ")" and "%" split off, spacer cells | "$" dropped, ")" / "%" glued to the number, empty cells removed -> Markdown table |
| Layout tables holding prose | single-column tables read as text |
| Very long sections (live) | capped per section (`LIVE_SECTION_CHARS`, 15,000) to bound CPU embedding time |

Key figures do **not** come from this text: the financials agent uses SEC XBRL company facts (annual = 10-K facts
with ~1-year duration; latest quarter = most recent 10-Q fact with ~3-month duration compared with the same quarter a
year earlier). The synthetic `financials.json` mirrors that structure.

## 4. Chunking, retrieval and the RAGAS-driven change
Each filing section is chunked with the shared structure-aware chunker (800 chars, tables whole); every chunk carries
ticker, form, filed date, section key and group, source and URL. Retrieval is always filtered to one ticker (0
cross-company chunks in evaluation) and, for briefing sections, to one section group.

RAGAS non-LLM context precision / recall on 10 filing questions:

| Fusion | k=3 F1 | k=6 F1 | k=10 F1 |
|---|---|---|---|
| vector only | 0.916 | 0.930 | 0.930 |
| BM25 only | 0.983 | 0.991 | 0.991 |
| hybrid, equal weights (initial) | 0.923 | 0.934 | 0.934 |
| **hybrid, BM25 weight 2 (chosen)** | 0.975 | **0.986** | 0.986 |
| hybrid, BM25 weight 3 | 0.983 | 0.991 | 0.991 |

Filing questions hinge on exact terms (product names, "basis points", dollar figures), so lexical ranking deserves
more weight. Weight 3 reproduces BM25-only behaviour (the vector ranking no longer changes the result); weight 2
captures nearly all the gain (+0.052 F1, MRR 0.90 -> 1.00) while keeping semantic matching for paraphrased questions
on long real filings that the 10-question set does not cover. `BM25_WEIGHT=2.0` is now the default.

## 5. Prompts and output
Versioned templates (`stockbrief/prompts.py`): `briefing/v1` - sections Business overview, Recent performance, Key
risks, Recent events, What to watch; cite `[n]`; copy numbers exactly; never compute; no buy/sell/hold, targets or
valuation judgements; style per role (advisor: plain language; analyst: precise). `qa/v1` for follow-ups. The
snapshot table and key-financials lines are rendered from computed data, not written by the LLM. Small models ignore
"2-4 bullets" and often skip citations, so the structure is enforced in code (max 5 bullets) and uncited bullets get a
citation **backfilled** from the evidence item they overlap most, or are marked *unattributed*.

## 6. Guardrails and compliance
| Guardrail | Where | Behaviour |
|---|---|---|
| Investment advice (should I buy, buy or sell, price target, will it go up, how much to allocate) | input | refused - recommendations follow the firm's research and suitability process |
| Material non-public information (insider, before it is announced) | input | refused, pointer to Compliance |
| Prompt injection | input | blocked |
| PII (account numbers, SSN, email, phone) | input + output | redacted |
| Recommendation language in the output (we recommend, price target, undervalued, investors should buy) | output | **bullet removed** and listed under "removed statements" for compliance review |
| Numeric grounding | output | every number must appear in the evidence (filings + computed snapshot / financials) |
| Disclaimer and data timestamps | output | always attached (quote time and source, "may be delayed" for live) |

## 7. Roles
| Role | Tasks | Live data | Style |
|---|---|---|---|
| financial_advisor | briefing, qa, quote | yes | advisor |
| research_analyst | briefing, qa, quote | yes | analyst |
| compliance_officer | briefing, qa, quote, **audit** (`GET /audit`) | yes | analyst |
| client_service_associate | quote | no | - |
| advisor_trainee | briefing (synthetic companies) | no | advisor |

## 8. Evaluation
`python -m eval.run_eval` (no LLM) and `python -m eval.ragas_eval --optimize`:

| Check | Result |
|---|---|
| Filing extraction (sections found, page furniture removed, hidden XBRL removed) | 6 / 6 filings |
| Retrieval hit@6 / MRR (10 questions across 10-K, 10-Q, 8-K) | 1.0 / 1.0 |
| Chunks from the wrong company | 0 |
| Guardrail precision / recall (14 cases) | 1.0 / 1.0 |
| Computed metrics vs hand calculation (growth, margin, P/E, loss-making P/E, quarter growth) | 5 / 5 |
| Compliance filter: advice statements removed / factual statements kept | 5 / 5, 4 / 4 |
| RAGAS context precision / recall (hybrid, BM25 weight 2, k=6) | 0.972 / 1.000 |
| Unit tests | 31 passed |

### 8.1 End-to-end LLM runs
| Run | Result |
|---|---|
| NWRB briefing, `financial_advisor`, synthetic data | answered in **232 s**; snapshot and key financials rendered from computed data; all bullets cited except two forward-looking "What to watch" judgements correctly marked *unattributed*; compliance review: pass |
| Repeat request, same scope | **< 1 s** from the briefing cache (30 min - quotes move) |
| Live data (no LLM): MSFT | quote 535.07 USD (Yahoo, delayed), P/E 29.8 and market cap computed; XBRL: FY2026 revenue $331.8 billion (+17.8%), latest 10-Q quarter +18.3%; EDGAR: latest 10-K, 10-Q and two 8-Ks parsed and indexed (135 chunks) |

LLM-judged RAGAS (`python -m eval.ragas_eval --llm 2`, local `llama3.2-judge` capped at 2 threads):

| Question | LLM context recall | Response groundedness | Faithfulness | Answer latency |
|---|---|---|---|---|
| Share of revenue from the three largest customers | 1.0 | 0.5 | judge failed (InstructorRetryException) | 65 s |
| Gross-margin impact of a 10-point actuator tariff | 1.0 | 1.0 | judge failed | 120 s |

As in project 07, the small local judge cannot run faithfulness reliably; context recall is perfect. Use a stronger
judge for generation metrics.

## 9. Monitoring
LangSmith traces (role, channel, provider tags; UI thumbs as feedback); `/metrics`
(`stockbrief_requests_total{intent,role,outcome}`, latency histogram, guardrail blocks, output flags);
`/metrics/summary`; `logs/audit.jsonl`, exposed to compliance through `GET /audit`.

## 10. Tech stack
Python 3.12, LangGraph 1.2 (parallel agents, conditional routing for briefing / quote / follow-up / refusal),
LangChain core 1.6, langchain-ollama, Ollama (`llama3.2`, `nomic-embed-text`), ChromaDB 1.5 + BM25 (weighted RRF),
BeautifulSoup 4.15 + lxml (EDGAR HTML), httpx (SEC EDGAR, Yahoo Finance chart API), FastAPI + Uvicorn, Streamlit,
LangSmith, RAGAS 0.4.3, pytest, ruff. Amazon Bedrock by configuration.

## 11. Trade-offs and limitations
- Yahoo's chart endpoint is unofficial and may be delayed or change; production would use a licensed market-data
  feed (the quote agent is one function to swap).
- Live mode indexes the first 15,000 characters of each section to bound CPU time; a GPU / Bedrock deployment can
  index full filings.
- XBRL concept coverage varies by company (e.g. banks do not report `GrossProfit`); missing values show as n/a.
- The 3B local model writes plain prose slowly on CPU; Claude on Bedrock would cut latency to seconds.
- Synthetic companies are fictional; nothing here is investment research.

Next steps: licensed quotes and consensus estimates, change detection between consecutive 10-Ks (new risk factors),
CRM integration (attach the briefing to the client meeting), firm-approved research notes as a source.
