# 03 - Supply Chain Knowledge Assistant

Enterprise knowledge assistant for **drug supply-chain and quality teams**: question answering, document
summarisation and semantic search over **PDF, Word, HTML, Markdown and CSV** - including **figures extracted
from documents and captioned by a vision model** (multimodal RAG). Llama-based model served over a REST API,
with versioned prompt templates and document-level access control.

> Portfolio prototype. Independent re-implementation of an enterprise knowledge-assistant pattern on
> **synthetic data** - fictional products, lots, sites and suppliers; not employer code or data.

| | |
|---|---|
| **Pattern** | Single-agent RAG workflow (LangGraph): guard -> classify task -> authorize -> retrieve (clearance filter) -> grade -> generate (prompt template) -> verify |
| **Models** | `llama3.2` (answers, via Ollama REST API), `nomic-embed-text` (embeddings), `gemma3:4b` (image captioning) |
| **Image extraction** | PyMuPDF (PDF images) + python-docx (inline Word pictures) -> PNG files -> vision captions -> `image` chunks |
| **Test URLs** | API **http://localhost:8003/docs** - UI **http://localhost:8503** - metrics **http://localhost:8003/metrics** |
| **Docs** | [Design document](docs/DESIGN.md) - [Slides](docs/Supply_Chain_Knowledge_Assistant.pptx) |

## Sample data (synthetic, committed) - `data/raw/`, regenerate with `python data/generate_data.py`
| File | Format | Classification | What it exercises |
|---|---|---|---|
| `SOP-CC-001_cold_chain_shipping.pdf` | PDF | internal | headings from font size, ruled table, **2 embedded diagrams** (excursion decision flowchart, distribution network) |
| `DEV-2026-014_temperature_excursion.docx` | Word | confidential | heading styles, timeline table, **embedded temperature chart** |
| `SUP-QUAL-2026_supplier_qualification.html` | HTML | internal | lists and a supplier scorecard table |
| `GDP-POL-001_good_distribution_practice.md` | Markdown | public | policy text |
| `inventory_lots.csv` | CSV | internal | 30 lot records (one chunk per row) |

The diagrams contain facts that appear nowhere else in text (e.g. the excursion decision rules, lane L3 ->
East Hub, the 12.6 C peak), so those questions can only be answered through image extraction + captioning.
Extracted images: `data/extracted/images/`; cached captions: `data/extracted/captions.json`.

## Run it
```powershell
cd 03-supply-chain-knowledge-assistant
pip install -r requirements.txt
ollama pull llama3.2; ollama pull nomic-embed-text; ollama pull gemma3:4b
copy .env.example .env                        # never commit .env
python -m supplykb.vision                     # caption extracted figures (cached; ~2-4 min per image on CPU)
python -m supplykb.ingest                     # 50 chunks: text, table, image, record
uvicorn supplykb.api:app --port 8003          # http://localhost:8003/docs
streamlit run ui/streamlit_app.py --server.port 8503
```
```powershell
curl -X POST http://localhost:8003/ask -H "X-API-Key: qa-demo-key" -H "Content-Type: application/json" `
     -d '{"question": "What should happen if a 2-8 C product is above 8 C for more than 2 hours cumulative?"}'
curl -X POST http://localhost:8003/summarize -H "X-API-Key: qa-demo-key" -H "Content-Type: application/json" `
     -d '{"doc_id": "DEV-2026-014", "style": "executive"}'
curl -X POST http://localhost:8003/search -H "X-API-Key: partner-demo-key" -H "Content-Type: application/json" `
     -d '{"query": "temperature excursion"}'
curl http://localhost:8003/documents -H "X-API-Key: partner-demo-key"        # only public documents
curl http://localhost:8003/images/SOP-CC-001_p1_img1 -H "X-API-Key: qa-demo-key" -o figure1.png
```

## Sample roles (document clearance)
| Role | Demo API key | Clearance | Tasks |
|---|---|---|---|
| `supply_planner` | `planner-demo-key` | internal | qa, search, summarize |
| `quality_assurance` | `qa-demo-key` | confidential | qa, search, summarize |
| `regulatory_affairs` | `ra-demo-key` | confidential | qa, search, summarize |
| `logistics_partner` | `partner-demo-key` | public | qa, search |

Clearance is applied as a **retrieval filter before ranking**, so restricted text never reaches the prompt.
`/images/{id}` and `/summarize` check the source document's classification too (403 / denied).

## Chunking and RAG
1. **Extract** every format to Markdown: PDF reading order is reconstructed by cutting each page into strips
   around tables and images; headings come from font size; Word heading styles and tables are kept; HTML lists
   and tables become Markdown.
2. **Images**: each extracted figure is replaced by a marker `[[IMAGE:<id>]]` at its position, captioned by the
   vision model (transcribe all text + describe the figure), and becomes its own `image` chunk under the
   section heading where it appeared (cites as `SOP-CC-001 > Monitoring`).
3. **Structure-aware chunks**: never cross a section, tables kept whole (up to 2,500 chars), 800-char target,
   contextual header `Title (ID) > Section`; CSV rows are one chunk each.
4. **Metadata** on every chunk: doc_id, title, section, content_type, classification, revision, image path.
5. `nomic-embed-text` -> ChromaDB, hybrid vector + BM25 retrieval; exact lookup for `LOT-` IDs in the question.

## Prompt templates
`supplykb/prompts.py` - versioned `ChatPromptTemplate`s: `qa/v1` (cite excerpts, copy numbers exactly, refuse
medical advice) and `summarize/v1` with styles `brief`, `detailed`, `executive`.

## Guardrails
Medical / dosing advice refused; release / reject / quarantine / recall **commands** refused (QA decides);
prompt injection blocked; emails / phones redacted; numeric and ID grounding (LOT-, SHP-, DEV-, SOP-, CAPA-, SUP-)
on every answer; clearance filter before retrieval.

## Tests, evaluation, RAGAS
```powershell
pytest -q                               # 18 tests (no model needed)
python -m eval.run_eval                 # retrieval hit@k by source type (text / table / image / record), access leakage, guardrails
python -m eval.run_eval --summaries     # + ROUGE-L of a generated summary
python -m eval.ragas_eval --optimize    # RAGAS non-LLM context precision / recall + retrieval sweep
python -m eval.ragas_eval --llm 2       # + LLM-judged faithfulness / groundedness / context recall
python -m eval.langsmith_eval           # LangSmith experiment (needs LANGSMITH_API_KEY)
```

## Monitoring
LangSmith tracing + feedback (`LANGSMITH_TRACING=true`), `/metrics` (`supplykb_requests_total{intent,role,outcome}`,
latency histogram, guardrail blocks), `/metrics/summary`, UI Metrics tab, `logs/audit.jsonl`.
