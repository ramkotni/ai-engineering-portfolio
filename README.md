# AI Engineering Portfolio

Eight end-to-end AI engineering prototypes built with **Python, LangGraph and LangChain**, each with synthetic
sample data, a REST API, a UI, role-based access, guardrails, evaluation (RAGAS where retrieval is involved),
LangSmith tracing, Prometheus-style metrics (01-05), tests, design documentation and slide decks.

> **Disclaimer.** These are independent re-implementations of architecture patterns I have worked with, built on
> **synthetic data** for demonstration. They contain no employer code, systems, documents or data; all names,
> IDs, amounts and documents are fictional.

| # | Project | Pattern | Highlights | API / UI |
|---|---|---|---|---|
| 01 | [Payment Operations Intelligence](01-payment-ops-intelligence/) | **Multi-agent** (LangGraph supervisor) + RAG over CSV + HTML | Intent, Search, RCA, Recommendation, Trend, Summary agents; pandas analytics; read-only guardrails | [:8001/docs](http://localhost:8001/docs) / [:8501](http://localhost:8501) |
| 02 | [Robotics Fleet Assistant](02-robotics-fleet-assistant/) | **Multi-agent** + RAG + fleet analytics | Diagnostics, Battery, Predictive Maintenance, Task Optimization, Ops Summary; zone-scoped roles; safety-override guardrails | [:8002/docs](http://localhost:8002/docs) / [:8502](http://localhost:8502) |
| 03 | [Supply Chain Knowledge Assistant](03-supply-chain-knowledge-assistant/) | **Multimodal RAG** (single-agent workflow) | PDF / Word / HTML / CSV ingestion, **image extraction + vision captions**, prompt templates, clearance-based access | [:8003/docs](http://localhost:8003/docs) / [:8503](http://localhost:8503) |
| 04 | [Project Feasibility Prediction](04-project-feasibility-ml/) | **Classical ML** + LangGraph advisor | scikit-learn pipeline, model comparison, interpretable logistic regression, PSI drift, explanations | [:8004/docs](http://localhost:8004/docs) / [:8504](http://localhost:8504) |
| 05 | [PlantAssist](05-plant-assist/) | **Routed RAG** (agentic workflow) | Routes to safety / maintenance / quality docs, safety-first policy, numeric grounding, AWS Bedrock path | [:8005/docs](http://localhost:8005/docs) / [:8505](http://localhost:8505) |
| 06 | [Health Member Services Copilot](06-health-member-services-copilot/) | **Multi-agent** (supervisor + policy RAG + claims agent) with critic loop and session memory | Cited benefit answers, claim-denial explanations, member-scoped claim authorization, PII redaction before the LLM, Bedrock Guardrails, **AWS Bedrock AgentCore** deploy path | [:8080](http://localhost:8080) (API + chat UI) |
| 07 | [Condition Briefing Assistant](07-healthcare-condition-briefing/) | **Parallel section agents** + RAG over a **complex PDF** | Healthcare scenario: structured briefing (standard of care, emerging treatments, key companies / institutions); two-column PDF, page-spanning table and figure extraction with vision captions; live ClinicalTrials.gov; one-slide pitch | [:8007/docs](http://localhost:8007/docs) / [:8507](http://localhost:8507) |
| 08 | [Stock Briefing Assistant](08-finance-stock-briefing/) | **Parallel data agents** + RAG over SEC filings | Finance scenario: quote + key financials (XBRL) + cited 10-K / 10-Q / 8-K summary; EDGAR HTML parser; compliance filter; live Yahoo Finance + SEC EDGAR; one-slide pitch | [:8008/docs](http://localhost:8008/docs) / [:8508](http://localhost:8508) |

## Business use cases and users
| # | Business problem | Who uses it (sample roles) |
|---|---|---|
| 01 | Failed, duplicate and late payments investigated by hand across tickets, reports and runbooks; repeat incidents and hidden month-end trends | Payment ops analysts and managers, finance executives, internal auditors, contracted IT support (amounts masked) |
| 02 | Robot failures that look alike, calendar-based maintenance, uneven workload and manual shift reports in a robotic warehouse | Robotics technicians, shift leads, fleet managers, site leadership, zone-limited contract technicians |
| 03 | Controlled documents in five formats with key facts inside figures, and confidential content that must not reach partners | Supply planners, quality assurance, regulatory affairs, external logistics partners (public documents only) |
| 04 | Inconsistent, reviewer-dependent funding decisions for new projects; risky projects approved and then slipping | Project managers, portfolio directors / PMO, the data scientist who owns the model, read-only stakeholders |
| 05 | Floor supervisors who know the question but not which binder (safety, maintenance, quality) holds the answer | Floor supervisors, maintenance technicians, quality engineers, EHS managers, contractors (safety only) |
| 06 | High volume of repetitive benefit and claim-denial questions in health-plan member services, with PHI that must stay protected | Plan members (portal / app chat, own claims only), member-services representatives, portal backends via API |
| 07 | Strategy teams spend days assembling the standard of care, pipeline and key players for each condition from complex PDFs, internal briefs and registries | Strategy analysts, service-line directors, executives, a physician advisor, external consultants (public sources only) |
| 08 | Advisors must get up to speed on a stock before a client call without reading 100-page filings, and without straying into recommendations | Financial advisors, research analysts, compliance officers, client-service associates (quotes only), advisor trainees |

Each project README has a **Business use case**, **Who uses it** (user, typical question, role, demo API key) and
**Tech stack** section. Projects 01-05 have a `docs/DESIGN.md` with the full design rationale; 06 documents its design
in its README, slides (with a code walkthrough) and AWS deploy guide.

Every project also has a TOGAF ADM delivery package in `<project>/docs/togaf/` (14 Markdown files: architecture
principles through requirements, ADRs, risks, backlog, test cases, CI/CD and operations). They are planning
documents for a hypothetical production roll-out; costs, sizing and schedules are labelled ESTIMATE with their
assumptions.

## Tech stack (versions tested)
| Layer | Technology |
|---|---|
| Language | Python 3.12.5 |
| Agent orchestration | LangGraph 1.2.14 |
| LLM framework | LangChain core 1.6.9, langchain-ollama 1.1.0, langchain-aws 1.8.1 (Bedrock in 05, 06) |
| Local models | Ollama 0.40.2: `llama3.2` (3B), `nomic-embed-text`, `gemma3:4b` (vision), `llama3.2-judge` (CPU-capped RAGAS judge) |
| Cloud models / hosting | Amazon Bedrock (Claude, Titan Text Embeddings v2) by configuration; Bedrock Guardrails, Bedrock AgentCore Runtime 1.24.1 (06) |
| Live data APIs | ClinicalTrials.gov API v2 (07), SEC EDGAR submissions / filings / XBRL company facts and Yahoo Finance chart API (08) |
| Vector store / search | ChromaDB 1.5.9 + in-process BM25 (hybrid with reciprocal rank fusion) |
| Document extraction | pdfplumber 0.11.10, PyMuPDF 1.28.2, python-docx 1.2.0, BeautifulSoup 4.15.0 + lxml (EDGAR HTML), PyYAML; `gemma3:4b` figure captions (03, 07) |
| Analytics / ML | pandas 3.0.6, numpy 2.5.4, scikit-learn 1.9.1, joblib 1.6.0 |
| API / UI | FastAPI 0.143.0 + Uvicorn 0.54.0, Streamlit 1.65.0 |
| Evaluation | RAGAS 0.4.3 (01-03, 05, 07, 08), golden set + LLM-as-judge quality gates and guardrail red-team suite (06), LangSmith experiments |
| Monitoring | LangSmith 0.14.7, Prometheus-format `/metrics`, JSONL audit logs |
| Quality | pytest 9.1.1, ruff 0.17.0 |
| Slides | pptxgenjs 3.12.0 (Node; decks 01-05, one-slide pitches 07-08 via `tools/deck/pitch.js`), python-pptx 1.0.2 (06) |

## Common building blocks
| Concern | Implementation |
|---|---|
| Orchestration | LangGraph `StateGraph` - supervisor + specialist agents (01, 02, 06) or a single-agent workflow (03, 05); deterministic plans, bounded loops; 06 adds a critic loop and checkpointer memory per session; 07 and 08 fan out to parallel section / data agents and join into one writer call followed by a grounding or compliance check |
| Models | Ollama locally (`llama3.2`, `nomic-embed-text`, `gemma3:4b` for vision); Amazon Bedrock by configuration (05 and 06 document the AWS path; 06 deploys to Bedrock AgentCore Runtime) |
| RAG | Extraction to Markdown -> structure-aware chunking (sections, whole tables, contextual headers) or one chunk per CSV row -> ChromaDB -> hybrid vector + BM25 retrieval with metadata filters (06: header-aware chunks, dense retrieval, Chroma or Bedrock Knowledge Bases) |
| Roles | 01-05: `roles.yaml` + `X-API-Key` demo keys; intent / task / source / zone / clearance permissions. 06: member-scoped claim authorization in code + optional API key |
| Guardrails | Prompt-injection and action/safety refusals, PII redaction, numeric and ID grounding of answers, slot grounding |
| Evaluation | Labelled datasets per project; `eval/run_eval.py`; **RAGAS** (`eval/ragas_eval.py`: non-LLM context precision/recall, retrieval-mode x top_k optimisation sweep, LLM-judged faithfulness / groundedness / context recall); LangSmith experiments. 06: golden set + LLM-as-judge quality gates, 31-case guardrail red-team suite |
| Monitoring | LangSmith tracing + user feedback; `GET /metrics` (Prometheus text) and `/metrics/summary`; `logs/audit.jsonl` (01-05). 06: LangSmith threads, automatic feedback scores, structured logs |
| Tests | pytest with fake LLMs and keyword retrievers - no model needed |

## Quick start
```powershell
# 1. Python env (one shared env for all projects, or one per project with its requirements.txt)
cd C:\AI\ai-engineering-portfolio
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r 01-payment-ops-intelligence/requirements.txt -r 02-robotics-fleet-assistant/requirements.txt `
            -r 03-supply-chain-knowledge-assistant/requirements.txt -r 04-project-feasibility-ml/requirements.txt `
            -r 05-plant-assist/requirements-app.txt -r 06-health-member-services-copilot/requirements-dev.txt `
            -r 07-healthcare-condition-briefing/requirements.txt -r 08-finance-stock-briefing/requirements.txt

# 2. Local models (Ollama)
ollama pull llama3.2; ollama pull nomic-embed-text; ollama pull gemma3:4b
ollama create llama3.2-judge -f tools/ollama/Modelfile.judge   # CPU-capped RAGAS judge (laptops without GPU)

# 3. Run any project (example: 01)
cd 01-payment-ops-intelligence
copy .env.example .env                 # .env files are never committed
python -m payops.ingest
uvicorn payops.api:app --port 8001     # http://localhost:8001/docs
```
Each project's README has its own run, test, evaluation and monitoring instructions.

## Run all projects at once
```powershell
.\scripts\start_all.ps1                  # APIs :8001-8008 + UIs :8501-8508 (06 on :8080); builds a missing index first
.\scripts\start_all.ps1 -Projects 07,08  # or just some of them
.\scripts\status.ps1                     # which APIs / UIs are up
.\scripts\stop_all.ps1                   # stop them all
```
Logs: `<project>\logs\api.log` and `ui.log`. Ollama must be running for LLM answers; guardrail refusals,
search and the ML predictions (04) work without it. All fifteen Python processes use about 3-4 GB of RAM - start only the projects you need.

| Project | Open in the browser | Try it with |
|---|---|---|
| 01 Payment Ops | http://localhost:8501 - API http://localhost:8001/docs | role `payment_analyst`: "Find past incidents like a wire rejected for a bad routing number" |
| 02 Robotics Fleet | http://localhost:8502 - API http://localhost:8002/docs | role `shift_lead`: "How many robots are active per zone?" |
| 03 Supply Chain KB | http://localhost:8503 - API http://localhost:8003/docs | role `quality_assurance`: "Find documents about temperature excursions" |
| 04 Feasibility ML | http://localhost:8504 - API http://localhost:8004/docs | role `project_manager`: score a project in the form |
| 05 PlantAssist | http://localhost:8505 - API http://localhost:8005/docs | role `floor_supervisor`: "How do I replace the main cylinder seal on the HP-200 press?" |
| 06 Member Services Copilot | http://localhost:8080 (chat UI; API on the same port, `POST /chat`) | member `M1001`: "Why was claim CLM-10002 denied and what can I do?" |
| 07 Condition Briefing | http://localhost:8507 - API http://localhost:8007/docs | role `strategy_analyst`: briefing on "heart failure"; Extraction tab shows how the PDF was parsed |
| 08 Stock Briefing | http://localhost:8508 - API http://localhost:8008/docs | role `financial_advisor`: briefing on `NWRB`; ask "Should my client buy HLXB?" (refused) |

In the API docs page, open an endpoint, click **Try it out** and put a demo key from the project's README
(e.g. `analyst-demo-key`) in the `x-api-key` field. In the UIs, pick the role from the sidebar.

## Test everything
```powershell
.\scripts\run_all_tests.ps1          # pytest in every project (no Ollama needed)
```

## Monitoring metrics
- **LangSmith**: add `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` to a project's `.env`; every
  graph run is traced with role / channel tags and user feedback is attached to runs.
- **Prometheus**: `GET http://localhost:800X/metrics` - request counts by intent/role/outcome, latency
  histograms, guardrail blocks, fallbacks, feedback (01-03, 05), predictions by risk band and OOD inputs (04).
  Point a Prometheus scrape job at these endpoints, or use `/metrics/summary` and each UI's Metrics tab.
- **Audit**: `logs/audit.jsonl` per project.

## CPU-only laptops
Set `OLLAMA_NUM_THREAD=2` and `OLLAMA_KEEP_ALIVE=60` in each `.env`, and use the `llama3.2-judge` model for
RAGAS (its thread cap lives in the model). Expect 1-3 minutes per LLM answer on CPU.

## Repository layout
```
01-payment-ops-intelligence/   02-robotics-fleet-assistant/   03-supply-chain-knowledge-assistant/
04-project-feasibility-ml/     05-plant-assist/               06-health-member-services-copilot/
07-healthcare-condition-briefing/  08-finance-stock-briefing/
  <package>/  data/ (generator + synthetic raw data)  eval/  tests/  ui/  docs/ (DESIGN.md + .pptx)  README.md
tools/deck/      shared slide-deck builder (pptxgenjs)     tools/ollama/   capped judge Modelfile
scripts/         start_all.ps1 / stop_all.ps1 / status.ps1 (ports in projects.ps1), run_all_tests.ps1 / .sh
```
