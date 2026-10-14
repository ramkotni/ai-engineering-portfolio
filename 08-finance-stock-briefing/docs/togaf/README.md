# Stock Briefing Assistant - TOGAF ADM Delivery Package

Planning and delivery package for taking the **Stock Briefing Assistant** prototype to a supervised, production
service for a wealth-management firm, structured by the TOGAF 10 ADM.

> **Basis.** Blank fields of `/prompt.md` are filled from this project's README, `docs/DESIGN.md` and code. Anything
> not in the repo is an **ASSUMPTION** (`A-xx`); every estimated number is marked **ESTIMATE** with its formula. The
> prompt's "ask questions, pause per phase" steps were skipped by agreement; open questions close each file. The
> offline companies (NWRB, HLXB) are fictional; live mode uses public sources. Numbers describe a hypothetical
> production roll-out. Not investment advice; not legal or regulatory advice.

## Project context (filled template)
| Field | Value |
|---|---|
| Application | Stock Briefing Assistant |
| Problem | Before a client call an advisor needs the quote, the financial trend and the main risks (quote screen + skimming a 100-page 10-K, latest 10-Q and 8-Ks) without sounding like an unsanctioned recommendation |
| AI type | LangGraph: 3 **parallel data agents** (quote, financials from XBRL, filings RAG) -> **one writer call** -> **compliance review** (recommendation-language filter, numeric grounding); EDGAR HTML parser; follow-up Q&A on filings; quote-only mode (no LLM) |
| Users / volume | ~450 users: advisors, research analysts, compliance officers, client-service associates, trainees (A-01). ESTIMATE 1,500 briefing requests/month (40% served from a 30-minute cache), 4,000 follow-ups, 30,000 quote lookups; peak 30 concurrent before market open |
| Cloud | AWS target (Bedrock by configuration); prototype local Ollama |
| Stack | Python 3.12, LangGraph, BeautifulSoup + lxml, ChromaDB + BM25 (BM25 weight 2), httpx, FastAPI, Streamlit, LangSmith, RAGAS |
| Data | SEC EDGAR filings (10-K, 10-Q, 8-K) and XBRL company facts (public, fair-access rules), market quotes (Yahoo chart API in the prototype - **not licensed for production**), client PII only if typed (redacted). Sensitivity: public data; briefings are firm communications subject to supervision |
| Compliance | SEC/FINRA communications and supervision rules (e.g. FINRA Rule 2210 on communications with the public, SEC Marketing Rule for advisers where applicable), books-and-records retention (SEC Rule 17a-4 / 204-2, WORM), Regulation Best Interest and suitability (no recommendations), MNPI controls, market-data licence terms, SEC EDGAR fair-access policy, SOC 2 (A-02; confirm applicability with the firm's Compliance) |
| Budget / timeline | ESTIMATE ~USD 0.47M build (people + 20% contingency), 5 months to GA |
| Integrations | Corporate IdP/SSO, CRM (client context, Phase 2), compliance archive/surveillance platform, licensed market-data vendor, SEC EDGAR |

## Files
| # | File | Phase |
|---|---|---|
| 00 | [00-preliminary.md](00-preliminary.md) | Preliminary |
| 01 | [01-architecture-vision.md](01-architecture-vision.md) | A |
| 02 | [02-business-architecture.md](02-business-architecture.md) | B |
| 03 | [03-information-systems.md](03-information-systems.md) | C |
| 04 | [04-technology-architecture.md](04-technology-architecture.md) | D |
| 05 | [05-opportunities-solutions.md](05-opportunities-solutions.md) | E |
| 06 | [06-migration-planning.md](06-migration-planning.md) | F |
| 07 | [07-product-backlog.md](07-product-backlog.md) | Backlog |
| 08 | [08-functional-spec.md](08-functional-spec.md) | Functional spec |
| 09 | [09-test-strategy.md](09-test-strategy.md) | Tests |
| 10 | [10-cicd-mlops.md](10-cicd-mlops.md) | CI/CD, LLMOps |
| 11 | [11-deployment-operations.md](11-deployment-operations.md) | G, H |
| 12 | [12-requirements-summary.md](12-requirements-summary.md) | Requirements, ADRs, risks, summary |

ID scheme: `REQ-STB-nnn`, `US-STB-nn`, `TC-STB-nn`, `ADR-STB-nn`, `R-STB-nn`.
