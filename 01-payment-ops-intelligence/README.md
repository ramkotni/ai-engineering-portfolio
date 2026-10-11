# 01 - Payment Operations Intelligence

Multi-agent assistant for **payment operations**: root cause analysis of failed payments, trend analysis,
recommendations and executive summaries over historical incidents and monitoring reports.

> Portfolio prototype. Independent re-implementation of a payment-operations intelligence pattern on
> **synthetic data** - not employer code, systems or data.

| | |
|---|---|
| **Pattern** | Multi-agent (LangGraph supervisor) + RAG (CSV + HTML) + pandas analytics |
| **Agents** | Intent, Search, RCA, Recommendation, Trend, Summary |
| **Models** | Ollama `llama3.2` + `nomic-embed-text` (local); Bedrock optional |
| **Vector store** | ChromaDB (2 collections: `incidents`, `knowledge`) + BM25 hybrid |
| **Test URLs** | API docs **http://localhost:8001/docs** - UI **http://localhost:8501** - metrics **http://localhost:8001/metrics** |
| **Docs** | [Design document](docs/DESIGN.md) - [Slides](docs/Payment_Ops_Intelligence.pptx) |

## What it does

| Ask | Agents that run | Example |
|---|---|---|
| RCA | Search -> RCA (-> Recommendation) | "Why are vendors being paid twice and what should we do?" |
| Recommendation | Search -> Recommendation | "What should we do to prevent settlement from missing the cut-off?" |
| Trend | Trend (pandas) | "Are duplicate payments increasing since the gateway release?" |
| Summary | Trend -> Summary (role-tailored) | "Give leadership a summary of payment operations health" |
| Search | Search | "Find past incidents like a wire rejected for a bad routing number" |

## Sample data (synthetic, committed)
`data/raw/` - regenerate with `python data/generate_data.py`:
- `incidents.csv` - 60 incidents (Apr-Sep 2026): system, payment type, category, severity, root cause, resolution, amount, MTTR
- `reports/payment_monitoring_2026_0{6,8,9}.html` - monitoring reports with headings, commentary and tables
- `business_rules.md` - runbook used by the Recommendation Agent (`PAY-RULES-001`)

Planted patterns for the Trend Agent: duplicate payments rise after gateway release v4.2 (Aug), timeouts
cluster at month-end, SFTP certificate expiry in June.

## Run it

Prerequisites: Python 3.11+, [Ollama](https://ollama.com) with `ollama pull llama3.2` and `ollama pull nomic-embed-text`.

```powershell
cd 01-payment-ops-intelligence
python -m venv .venv; .venv\Scripts\Activate.ps1        # or use the shared portfolio .venv
pip install -r requirements.txt
copy .env.example .env                                   # never commit .env

python -m payops.ingest                                  # build ChromaDB (60 incidents + 19 chunks, ~45 s)
uvicorn payops.api:app --port 8001                       # API  -> http://localhost:8001/docs
streamlit run ui/streamlit_app.py --server.port 8501     # UI   -> http://localhost:8501
python -m payops.cli ask "Why are vendors being paid twice?" --role payment_analyst --trace
```

### Try the API
```powershell
curl -X POST http://localhost:8001/ask -H "X-API-Key: analyst-demo-key" -H "Content-Type: application/json" `
     -d '{"question": "Why are vendors being paid twice and what should we do?"}'
curl -X POST http://localhost:8001/ask -H "X-API-Key: exec-demo-key" -H "Content-Type: application/json" `
     -d '{"question": "Give leadership a summary of payment operations health"}'
curl -X POST http://localhost:8001/feedback -H "X-API-Key: analyst-demo-key" -H "Content-Type: application/json" `
     -d '{"run_id": "<run_id from /ask>", "score": 1}'
curl http://localhost:8001/roles
curl http://localhost:8001/metrics
```

## Sample roles

| Role | Demo API key | Can run | Amounts |
|---|---|---|---|
| `payment_analyst` | `analyst-demo-key` | search, rca, recommendation, trend, summary | visible |
| `operations_manager` | `manager-demo-key` | all | visible |
| `executive` | `exec-demo-key` | trend, summary (executive style) | visible |
| `auditor` | `auditor-demo-key` | search, trend, summary | visible |
| `support_engineer` | `support-demo-key` | search, rca | **masked** |

Defined in [payops/roles.yaml](payops/roles.yaml). Requests outside a role's permissions return `outcome: denied`.

## Guardrails
- **Read-only**: commands to release / approve / cancel / re-send payments or change vendor bank details are refused (questions about the process are answered).
- **Prompt injection** blocked before any LLM call.
- **Bank data / PII** (account and routing numbers, emails, phones) redacted in input and output.
- **Numeric grounding**: every number in an answer must exist in the retrieved incidents, analytics or question.
- **Incident-ID grounding**: cited `PAY-INC-*` IDs must be in the evidence.
- **Slot grounding**: filters the Intent Agent extracts (system, payment type, months) are kept only if the question mentions them.
- **RBAC**: intent permissions and amount masking per role.

## Chunking and RAG
- **CSV incidents -> one document per row.** An incident is the unit of evidence; splitting it would separate symptom, root cause and resolution. All columns become metadata (category, system, severity, month, amount) for filtered search.
- **HTML reports -> Markdown** (BeautifulSoup: headings, paragraphs, lists, tables) -> **structure-aware chunks**: never cross a section, tables kept whole (up to 2,500 chars), 800-char target, contextual header `Title (ID) > Section`.
- **Embeddings**: `nomic-embed-text` with `search_document:` / `search_query:` prefixes -> ChromaDB (cosine).
- **Retrieval**: hybrid vector + BM25 with reciprocal rank fusion; metadata filter by failure category from the Intent Agent.

## Tests
```powershell
pytest -q            # 29 tests - fake LLM + keyword retriever over the real sample data; no Ollama needed
```
Covers ingestion (CSV rows, HTML sections and tables), analytics vs independent pandas, intent fallback,
slot grounding, guardrails, RBAC, every graph path (RCA + recommendation, denied, blocked, trend fallback,
amount masking, invented incident ID), metrics/audit, and the API (auth, roles, metrics).

## Evaluation and RAGAS
```powershell
python -m eval.run_eval                      # intent, retrieval hit@k / MRR / precision@k, guardrails, analytics
python -m eval.run_eval --llm                # + Intent Agent accuracy with the LLM
python -m eval.ragas_eval --optimize         # RAGAS non-LLM context precision / recall + retrieval sweep
python -m eval.ragas_eval --llm 3            # + LLM-judged faithfulness and context recall on 3 answers
python -m eval.langsmith_eval                # LangSmith experiment (needs LANGSMITH_API_KEY)
```
Results are written to `eval/results/`. Current numbers are in [docs/DESIGN.md](docs/DESIGN.md#8-evaluation).

## Monitoring
- **LangSmith**: set `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT` in `.env`. Every agent, LLM call and retrieval is traced with tags `role:*`, `channel:*`, `provider:*`; feedback from the UI / `POST /feedback` is attached as `user_rating`.
- **Prometheus metrics**: `GET /metrics` - `payops_requests_total{intent,role,outcome}`, `payops_request_latency_seconds` histogram, `payops_guardrail_blocks_total{category}`, `payops_intent_fallback_total`, `payops_feedback_total`. JSON view: `GET /metrics/summary`, and the UI "Metrics" tab.
- **Audit log**: `logs/audit.jsonl` - one line per question and feedback (role, intent, plan, citations, guardrails, latency).

## Project layout
```
payops/       config, llm, loaders, chunking, ingest, retrieval, analytics, agents, graph, rbac, roles.yaml,
              guardrails, observability, service, api, cli
data/         generate_data.py + raw/ (synthetic CSV, HTML, Markdown)
eval/         datasets/, run_eval.py, ragas_eval.py, ragas_utils.py, langsmith_eval.py, results/
tests/        conftest.py (fakes), test_core.py, test_graph.py
ui/           streamlit_app.py
docs/         DESIGN.md, deck_spec.js, Payment_Ops_Intelligence.pptx
```
