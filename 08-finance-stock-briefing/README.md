# 08 - Stock Briefing Assistant (Finance)

Helps a wealth-management **advisor get up to speed on a stock**: current quote and price metrics, key financials
from XBRL data, and a cited summary of the latest **SEC filings** (10-K, 10-Q, 8-K) - business, recent performance,
risks, recent events and what to watch. Informational only, with a compliance filter that removes recommendation
language.

> Portfolio prototype. Offline mode uses two **fictional** companies (NWRB - Northwind Robotics, HLXB - Helix
> Biologics; tickers verified unused on the SEC list). Live mode uses Yahoo Finance quotes and SEC EDGAR for any US
> ticker. Not investment advice.

| | |
|---|---|
| **Pattern** | LangGraph: 3 parallel data agents (quote, financials, filings) -> one writer call -> compliance review; RAG over parsed EDGAR filings |
| **Models** | Ollama `llama3.2` (writer), `nomic-embed-text` (embeddings); Amazon Bedrock by configuration |
| **Live data** | Yahoo Finance chart API (quotes, no key) + SEC EDGAR (filings and XBRL financials; needs `SEC_USER_AGENT`) |
| **Test URLs** | API docs **http://localhost:8008/docs** - UI **http://localhost:8508** - metrics **http://localhost:8008/metrics** |
| **Docs** | [Design document](docs/DESIGN.md) - [Pitch slide](docs/Stock_Briefing_Pitch.pptx) |

## Business use case
| | |
|---|---|
| **Problem** | Before a client call an advisor needs the quote, the financial trend and the main risks - which means a quote screen plus skimming a 100-page 10-K, the latest 10-Q and recent 8-Ks. Few advisors have time, and anything they say must not sound like an unsanctioned recommendation. |
| **What it does** | One briefing per ticker in minutes: snapshot (price, change, 52-week range, 1-year change, market cap, P/E), key financials, and cited bullets from the filings; follow-up questions answered from the filings; a quote-only mode for client-service staff. |
| **Value (pilot targets)** | Preparation time per stock from ~30-60 minutes to a few minutes, consistent coverage of risks and recent events, every figure traceable to a filing or a data feed, supervised output. Targets to measure in a pilot, not prototype results. |

## Who uses it
| User | Typical request | Role (`stockbrief/roles.yaml`) | Demo API key |
|---|---|---|---|
| Financial advisor | Briefing on HLXB before a client meeting | `financial_advisor` - briefing, qa, quote, live data | `advisor-demo-key` |
| Research analyst | "What new tariff hit NWRB in May 2026?" | `research_analyst` - briefing, qa, quote, live data, detailed style | `analyst-demo-key` |
| Compliance officer | Review briefings and the audit trail | `compliance_officer` - all tasks + `GET /audit` | `compliance-demo-key` |
| Client-service associate | Quote look-up for a client on the phone | `client_service_associate` - quote only | `associate-demo-key` |
| Advisor trainee | Practice briefings on the demo companies | `advisor_trainee` - briefing, synthetic data only | `trainee-demo-key` |

## Tech stack
| Layer | Technology |
|---|---|
| Orchestration | LangGraph 1.2 - parallel data agents, conditional routing (briefing / quote / follow-up / refusal) |
| LLM framework | LangChain core 1.6 (versioned `ChatPromptTemplate`s), langchain-ollama 1.1 |
| Models | Ollama 0.40: `llama3.2` (3B), `nomic-embed-text`; Amazon Bedrock option |
| Filing extraction | BeautifulSoup 4.15 + lxml - EDGAR HTML to Item sections (TOC and page furniture handled) |
| Structured data | SEC XBRL company facts (live) / XBRL-like JSON (synthetic); metrics computed in Python |
| Market data | Yahoo Finance chart API via httpx (live) / synthetic snapshot |
| Retrieval | ChromaDB 1.5 + BM25, weighted reciprocal rank fusion (BM25 weight 2, tuned with RAGAS); ticker + section filters |
| API / UI | FastAPI + Uvicorn, Streamlit (briefing with price chart, ask the filings, metrics) |
| Evaluation / monitoring | RAGAS 0.4.3, offline eval suite, LangSmith, Prometheus-format `/metrics`, audit log with `/audit` endpoint |
| Quality | pytest (31 tests, no model or network needed), ruff |

## Sample data (synthetic, committed) - regenerate with `python data/generate_data.py`
| File | What it holds |
|---|---|
| `companies.json` | profiles of NWRB and HLXB |
| `quotes.json` | quote snapshot + 52 weekly closes per ticker |
| `financials.json` | FY2023-FY2025 annual facts and Q2 2026 vs Q2 2025 (XBRL-like, USD millions) |
| `filings/<TICKER>/` | EDGAR-style HTML 10-K (with table of contents, page furniture, split-span headings, "$" cells), 10-Q, 8-K, `filings_index.json` |

Helix Biologics' pipeline (HLX-INS7, HLX-SERCA, ...) is the same one in project 07's trial registry - the 8-K
reports the Phase 3 HLX-INS7 topline results for trial SYN-DM-203.

## Run it
```powershell
cd 08-finance-stock-briefing
pip install -r requirements.txt                    # or use the shared portfolio .venv
copy .env.example .env                             # never commit .env; CPU laptops: OLLAMA_NUM_THREAD=2
python -m stockbrief.ingest                        # parse + index the synthetic filings (14 chunks)
uvicorn stockbrief.api:app --port 8008             # API -> http://localhost:8008/docs
streamlit run ui/streamlit_app.py --server.port 8508   # UI -> http://localhost:8508
python -m stockbrief.cli brief NWRB --role financial_advisor --trace
python -m stockbrief.cli ask "What were the HLX-INS7 Phase 3 topline results?"
```
Or from the portfolio root: `.\scripts\start_all.ps1 -Projects 08`.

**Live mode (any US ticker):** add `SEC_USER_AGENT=Your Company your.name@example.com` to `.env` (SEC requires a
contact in the User-Agent), then `python -m stockbrief.cli brief MSFT --live` or toggle *Live data* in the UI. The
first briefing of a ticker downloads and indexes its latest 10-K, 10-Q and two 8-Ks (cached in `data/cache/`, which is
git-ignored). Quotes work without `SEC_USER_AGENT`.

### Try the API
```powershell
$h = @{ "X-API-Key" = "advisor-demo-key" }
Invoke-RestMethod http://localhost:8008/briefing -Method Post -Headers $h -ContentType "application/json" -Body '{"company": "HLXB"}'
Invoke-RestMethod "http://localhost:8008/quote/NWRB" -Headers @{ "X-API-Key" = "associate-demo-key" }
Invoke-RestMethod http://localhost:8008/ask -Method Post -Headers $h -ContentType "application/json" `
  -Body '{"question": "Should my client buy HLXB?"}'                        # refused: investment advice
Invoke-RestMethod "http://localhost:8008/audit?limit=5" -Headers @{ "X-API-Key" = "compliance-demo-key" }
```
Endpoints: `POST /briefing`, `GET /quote/{ticker}`, `POST /ask`, `GET /filings/{ticker}`, `GET /audit`,
`POST /feedback`, `GET /roles`, `GET /health`, `GET /metrics`, `GET /metrics/summary`.

## Guardrails
Investment-advice requests (buy/sell/hold, price targets, "will it go up", allocations) and MNPI requests are refused;
prompt injection blocked; account numbers, SSN, email and phone redacted; the **compliance review removes any bullet
with recommendation language** and lists it for compliance; every number in the briefing must exist in the filings
or the computed market / financial data; disclaimer and data timestamps always attached.

## Tests, evaluation, RAGAS
```powershell
pytest                                      # 31 tests - parser, metrics, guardrails, workflow, API (no model, no network)
python -m eval.run_eval                     # extraction, retrieval, guardrails, computed metrics, compliance filter
python -m eval.run_eval --briefings 2       # + end-to-end LLM briefings (slow on CPU)
python -m eval.ragas_eval --optimize        # RAGAS precision / recall + sweep over fusion weight and k
python -m eval.ragas_eval --llm 2           # + LLM-judged faithfulness / groundedness / context recall
python -m eval.langsmith_eval --limit 4     # LangSmith experiment (needs LANGSMITH_API_KEY)
```
Current results (details in [DESIGN.md section 8](docs/DESIGN.md#8-evaluation)): extraction 6/6 filings; retrieval
hit@6 1.0, MRR 1.0, 0 cross-company chunks; guardrails 1.0 / 1.0; computed metrics 5/5; compliance filter 5/5 advice
removed, 4/4 facts kept; RAGAS precision 0.972 / recall 1.0 after raising the BM25 weight from 1 to 2 (F1 0.934 -> 0.986).

## Monitoring
LangSmith traces per request (every agent, retrieval and LLM call; role / channel tags; thumbs feedback from the UI);
Prometheus text at `/metrics`, JSON at `/metrics/summary`; audit trail in `logs/audit.jsonl`, readable by the
compliance role at `GET /audit`.

## Project layout
```
stockbrief/  filings (EDGAR HTML parser) | edgar (SEC client) | market (quotes + price metrics) | financials (XBRL + metrics)
             companies | ingest | chunking | retrieval | graph (LangGraph) | prompts | guardrails | rbac + roles.yaml
             service | api | cli | observability
data/        generate_data.py, raw/ (synthetic market data + filings); cache/ (live downloads, git-ignored)
eval/        datasets/, run_eval.py, ragas_eval.py, langsmith_eval.py, results/
tests/       parser, metrics, guardrails, workflow and API tests
ui/          Streamlit app        docs/  DESIGN.md, pitch slide
```
