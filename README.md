# AI Engineering Portfolio

Five end-to-end AI engineering prototypes built with **Python, LangGraph and LangChain**, each with synthetic
sample data, a REST API, a UI, role-based access, guardrails, evaluation (RAGAS where retrieval is involved),
LangSmith tracing, Prometheus-style metrics, tests, a design document and a slide deck.

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

## Common building blocks (in every project)
| Concern | Implementation |
|---|---|
| Orchestration | LangGraph `StateGraph` - supervisor + specialist agents (01, 02) or a single-agent workflow (03, 05); deterministic plans, bounded loops |
| Models | Ollama locally (`llama3.2`, `nomic-embed-text`, `gemma3:4b` for vision); Amazon Bedrock by configuration (05 documents the AWS path) |
| RAG | Extraction to Markdown -> structure-aware chunking (sections, whole tables, contextual headers) or one chunk per CSV row -> ChromaDB -> hybrid vector + BM25 retrieval with metadata filters |
| Roles | `roles.yaml` + `X-API-Key` demo keys; intent / task / source / zone / clearance permissions |
| Guardrails | Prompt-injection and action/safety refusals, PII redaction, numeric and ID grounding of answers, slot grounding |
| Evaluation | Labelled datasets per project; `eval/run_eval.py`; **RAGAS** (`eval/ragas_eval.py`: non-LLM context precision/recall, retrieval-mode x top_k optimisation sweep, LLM-judged faithfulness / groundedness / context recall); LangSmith experiments |
| Monitoring | LangSmith tracing + user feedback; `GET /metrics` (Prometheus text) and `/metrics/summary`; `logs/audit.jsonl` |
| Tests | pytest with fake LLMs and keyword retrievers - no model needed |

## Quick start
```powershell
# 1. Python env (one shared env for all projects, or one per project with its requirements.txt)
cd C:\AI\ai-engineering-portfolio
python -m venv .venv; .venv\Scripts\Activate.ps1
pip install -r 01-payment-ops-intelligence/requirements.txt -r 03-supply-chain-knowledge-assistant/requirements.txt `
            -r 04-project-feasibility-ml/requirements.txt -r 05-plant-assist/requirements-app.txt

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
04-project-feasibility-ml/     05-plant-assist/
  <package>/  data/ (generator + synthetic raw data)  eval/  tests/  ui/  docs/ (DESIGN.md + .pptx)  README.md
tools/deck/      shared slide-deck builder (pptxgenjs)     tools/ollama/   capped judge Modelfile
scripts/         run_all_tests.ps1 / .sh
```
