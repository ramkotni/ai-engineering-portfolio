# 08 - Functional Specification

## Modules
| Module | Inputs | Processing | Outputs | Validations / errors |
|---|---|---|---|---|
| Input guard | request text | Investment-advice detector (should I buy, buy or sell, price target, will it go up, how much to allocate), MNPI detector (insider, before announced), injection, PII redaction (account numbers, SSN, email, phone), length | clean request or refusal | Refusal wording from Compliance-owned catalog; blocked -> audit outcome |
| Resolve ticker | company name or ticker | Match synthetic list or SEC ticker/CIK map | ticker, CIK | Unknown -> "ticker not found" |
| Authorize | role, task, live flag | `roles.yaml`: tasks, live_data, style; trainee synthetic only | proceed or denied | Denied lists allowed tasks |
| Quote agent | ticker | Licensed vendor snapshot or synthetic; metrics: change, 52-week range, 1-year change, market cap, P/E (loss-making -> "n/m") | snapshot with as-of time and source | Feed error -> "unavailable" with last good time |
| Financials agent | ticker | XBRL facts: annual (10-K ~1-year duration), latest quarter (10-Q ~3-month duration) vs same quarter prior year; growth, margins computed in Python | key financials lines | Missing facts -> "not reported" |
| Filings agent | ticker | Ensure filings ingested (latest 10-K, 10-Q, two 8-Ks); retrieve per section group with ticker filter, hybrid BM25 weight 2, k=6 | evidence items with citations | No filing -> section unavailable |
| Filing parser | EDGAR HTML | See file 03 techniques; items by part for 10-Q (`I-2`, `II-1A`) | Markdown items | Required item missing -> flag |
| Writer | evidence, style | One call: sections (Business overview, Recent performance, Key risks, Recent events, What to watch); cite `[n]`; copy numbers; never compute; no advice; style advisor/analyst | bullets | LLM failure -> data-only briefing |
| Structure enforcement | draft | Max 5 bullets/section; backfill missing citation from best-overlapping evidence or mark *unattributed* | bullets | - |
| Compliance review | bullets | Lexicon match (we recommend, price target, undervalued, investors should buy ...) plus rule patterns; remove and log; numeric grounding (numbers in evidence/computed data/question) | filtered bullets, removed statements, flags | Ungrounded number -> flagged; filter error -> briefing withheld |
| Follow-up Q&A | question, ticker | retrieve -> answer -> verify; ticker scoped | answer + citations | Not in filings -> say so |
| Archive | final briefing | Write to WORM with versions and timestamps, then display | archive id | Failure -> not shown |
| Audit | every request | Log user, role, task, ticker, outcome, flags | `/audit` for compliance | Never blocks request except archive failure for briefings |

## Roles and permissions
| Role | briefing | qa | quote | audit | live data | style |
|---|---|---|---|---|---|---|
| financial_advisor | Y | Y | Y | N | Y | advisor |
| research_analyst | Y | Y | Y | N | Y | analyst |
| compliance_officer | Y | Y | Y | Y | Y | analyst |
| client_service_associate | N | N | Y | N | N | - |
| advisor_trainee | Y (synthetic) | N | N | N | N | advisor |

## UI behavior
Ticker box with live/synthetic toggle; snapshot card with price chart (52 weekly closes), "as of" time and source and "may be delayed" notice; key financials table; five sections with source chips; "unattributed" badges; a banner "For internal preparation; not investment advice; not for distribution to clients unless approved"; refusal card explaining why and who to contact; removed-statements panel visible to Compliance only; Compliance audit tab with filters and CSV export; feedback buttons.

## AI behavior specification
| Aspect | Spec |
|---|---|
| Tone | Neutral, factual, plain language for advisors; precise for analysts; no promotional adjectives; balanced (positives and risks) |
| Citations | `[n]` to filing form, section, filed date; computed values cite the data source and period |
| Refusals | "I can summarise public filings and market data. Recommendations and price targets follow the firm's research and suitability process." MNPI: "Please contact Compliance." |
| Confidence | Missing evidence -> say so; low retrieval -> "filings do not contain"; never infer forward-looking statements; "What to watch" lists items the filings flag (risk factors, guidance, pending events) |
| Numbers | Only from filings or computed data; rounding rules fixed (percent 1 decimal, currency in millions/billions per filing) |
| Fallback to human | Removed statements, unattributed bullets, refusals -> Compliance/advisor review |
| Language | English; US filings |

## Open questions
Final lexicon and paraphrase-detection approach; approved disclaimer text; policy for sharing with clients.
