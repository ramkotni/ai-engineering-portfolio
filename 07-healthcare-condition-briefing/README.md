# 07 - Condition Briefing Assistant (Healthcare)

Generates a **structured briefing for a medical condition** for a health-system strategy team: current standard of
care, emerging treatments in development, and key companies and institutions - from a **complex PDF guideline**
(two columns, multi-page table, figures), HTML and Word documents and a trial registry, with an optional **live
ClinicalTrials.gov** mode.

> Portfolio prototype on **synthetic data**. Clinical content is a simplified synthetic summary for demonstrating
> document AI - **not clinical guidance**. All companies, institutions, trials and health-system figures are fictional.

| | |
|---|---|
| **Pattern** | LangGraph: planner -> 4 parallel section agents -> one writer call -> grounding check; RAG over a layout-aware extraction of complex documents |
| **Models** | Ollama `llama3.2` (writer), `nomic-embed-text` (embeddings), `gemma3:4b` (figure captions); Amazon Bedrock by configuration |
| **Live data** | ClinicalTrials.gov API v2 (no key) - any condition |
| **Test URLs** | API docs **http://localhost:8007/docs** - UI **http://localhost:8507** - metrics **http://localhost:8007/metrics** |
| **Docs** | [Design document](docs/DESIGN.md) (section 3 explains the PDF extraction) - [Pitch slide](docs/Condition_Briefing_Pitch.pptx) |

## Business use case
| | |
|---|---|
| **Problem** | Strategy teams spend days assembling the same picture for each condition - what the guideline recommends, what is in the pipeline and who is behind it - from complex PDFs, internal briefs and registries. Facts hide in multi-page tables and figures. |
| **What it does** | In minutes: a briefing with fixed sections (executive summary, standard of care, emerging treatments with a late-stage table, key companies and institutions, strategic considerations for internal users), every statement traceable to a numbered source; follow-up questions on the same sources. |
| **Value (pilot targets)** | Briefing preparation from days to minutes, consistent format across conditions, counts and rankings that are computed rather than guessed. Targets to measure in a pilot, not prototype results. |

## Who uses it
| User | Typical request | Role (`medbrief/roles.yaml`) | Demo API key |
|---|---|---|---|
| Strategy analyst | Briefing on HFrEF, follow-up "When is CRT-D indicated?" | `strategy_analyst` - internal clearance, live data | `analyst-demo-key` |
| Service-line director | Briefing with strategic considerations | `service_line_director` - internal, live data | `director-demo-key` |
| Executive (CSO / COO) | Short executive briefing | `executive` - briefing only, no live data | `exec-demo-key` |
| Physician advisor | Clinical review of the standard-of-care section | `clinical_advisor` - internal, live data, clinical style | `clinical-demo-key` |
| External consultant | Briefing from public sources only | `external_consultant` - public clearance, no internal strategy documents | `consultant-demo-key` |

## Tech stack
| Layer | Technology |
|---|---|
| Orchestration | LangGraph 1.2 - parallel fan-out / join of section agents, conditional routing (briefing / follow-up / refusal) |
| LLM framework | LangChain core 1.6 (versioned `ChatPromptTemplate`s), langchain-ollama 1.1 |
| Models | Ollama 0.40: `llama3.2` (3B), `nomic-embed-text`, `gemma3:4b` vision; Amazon Bedrock option |
| Document extraction | pdfplumber 0.11 (text, tables, reading order), PyMuPDF 1.28 (images), python-docx 1.2, BeautifulSoup 4.15 |
| Retrieval | ChromaDB 1.5 + BM25 hybrid (reciprocal rank fusion), clearance and condition filters before ranking |
| Live data | httpx -> ClinicalTrials.gov API v2 |
| API / UI | FastAPI + Uvicorn, Streamlit (Briefing, Ask, **Extraction**, Metrics tabs) |
| Evaluation / monitoring | RAGAS 0.4.3, offline eval suite, LangSmith, Prometheus-format `/metrics`, JSONL audit log |
| Quality | pytest (37 tests, no model needed), ruff |

## Sample data (synthetic, committed) - regenerate with `python data/generate_data.py`
| File | Format | Classification | What it exercises |
|---|---|---|---|
| `CARD-GL-2026_hfref_guideline_summary.pdf` | **complex PDF**, 4 pages | public | running header/footer, two-column body, ruled table continued across a page break with repeated header, treatment-algorithm flowchart and pipeline bar chart (content only in the images), footnotes |
| `DM-GL-2026_type2_diabetes_care_summary.html` | HTML | public | headings, drug-class table, lists |
| `STRAT-2026_cardiometabolic_service_line.docx` | Word | **internal** | health-system performance, partnership table, embedded admissions chart |
| `pipeline_trials.csv` | CSV | public | 26 programs (HFrEF, type 2 diabetes): mechanism, modality, phase, status, sponsor, lead site |

Extraction output (committed for review): `data/extracted/markdown/*.md`, `data/extracted/images/*.png`,
`data/extracted/captions.json`, `data/extracted/extraction_report.json`.

## How the PDF is extracted (summary - details in [DESIGN.md section 3](docs/DESIGN.md#3-extraction---how-the-complex-pdf-is-handled))
1. **Headers / footers**: lines in the top / bottom 8% that repeat on most pages (digits masked) are removed.
2. **Reading order**: each page is cut into strips around tables and images; inside a strip, rows that cross the centre
   gutter are full-width, others belong to a column - left column is read before the right column.
3. **Tables**: pdfplumber ruled-table detection -> Markdown; a table whose header matches the previous table's header is
   **merged across the page break**.
4. **Images**: PyMuPDF extracts each figure with its position -> PNG + `[[IMAGE:id]]` marker in the text flow ->
   `gemma3:4b` caption (transcription + description, cached) -> its own retrievable chunk. Drug names in a caption that
   appear nowhere else in the document are flagged for verification (it caught a real misread).
5. **Headings** from font size, **footnotes** from small type, **metadata** from the document-ID line.

```powershell
python -m medbrief.loaders data/raw/CARD-GL-2026_hfref_guideline_summary.pdf   # print stats + extracted Markdown
```

## Run it
Prerequisites: Python 3.11+, Ollama with `ollama pull llama3.2`, `ollama pull nomic-embed-text`, `ollama pull gemma3:4b`.

```powershell
cd 07-healthcare-condition-briefing
pip install -r requirements.txt                    # or use the shared portfolio .venv
copy .env.example .env                             # never commit .env; CPU laptops: OLLAMA_NUM_THREAD=2
python data/generate_data.py                       # optional - the data is committed
python -m medbrief.ingest                          # extract, caption figures (cached), chunk, embed -> ChromaDB (50 chunks)
uvicorn medbrief.api:app --port 8007               # API -> http://localhost:8007/docs
streamlit run ui/streamlit_app.py --server.port 8507   # UI -> http://localhost:8507
python -m medbrief.cli brief "heart failure" --role strategy_analyst --trace
python -m medbrief.cli brief "atrial fibrillation" --live      # any condition via ClinicalTrials.gov
python -m medbrief.cli ask "When is CRT-D indicated according to the algorithm?"
```
Or start everything from the portfolio root: `.\scripts\start_all.ps1 -Projects 07`.

### Try the API
```powershell
$h = @{ "X-API-Key" = "analyst-demo-key" }
Invoke-RestMethod http://localhost:8007/briefing -Method Post -Headers $h -ContentType "application/json" `
  -Body '{"condition": "heart failure with reduced ejection fraction", "source": "synthetic"}'
Invoke-RestMethod http://localhost:8007/ask -Method Post -Headers $h -ContentType "application/json" `
  -Body '{"question": "How many active HFrEF device programs are there?"}'
Invoke-RestMethod http://localhost:8007/extraction -Headers @{ "X-API-Key" = "consultant-demo-key" }   # internal docs hidden
```
Endpoints: `POST /briefing`, `POST /ask`, `GET /conditions`, `GET /documents`, `GET /extraction`, `GET /images/{id}`,
`POST /feedback`, `GET /roles`, `GET /health`, `GET /metrics`, `GET /metrics/summary`.

## Guardrails
Patient-specific advice refused ("should my father start an SGLT2 inhibitor?"); prompt injection blocked; PHI
(MRN, DOB, SSN, phone, email) redacted; every number and trial / document ID in the output must exist in the
evidence; second-person treatment language flagged; uncited bullets get a citation backfilled from the evidence
they match, or are marked *unattributed*; disclaimer always attached. Role clearance is enforced before retrieval.

## Tests, evaluation, RAGAS
```powershell
pytest                                      # 37 tests, fake LLM + keyword retriever, no Ollama needed
python -m eval.run_eval                     # extraction 8/8, retrieval, access control, guardrails, registry analytics
python -m eval.run_eval --briefings 2       # + end-to-end LLM briefings (slow on CPU)
python -m eval.ragas_eval --optimize        # RAGAS context precision / recall + retrieval sweep
python -m eval.ragas_eval --llm 2           # + LLM-judged faithfulness / groundedness / context recall
python -m eval.langsmith_eval --limit 4     # LangSmith experiment (needs LANGSMITH_API_KEY)
```
Current results (details in [DESIGN.md section 9](docs/DESIGN.md#9-evaluation)): extraction 8/8; retrieval hit@6 1.0,
MRR 0.917 across 11 source types; 0 internal chunks to the public role; guardrails 1.0 / 1.0; RAGAS hybrid k=6
precision 0.958 / recall 0.892 (kept after the sweep).

## Monitoring
LangSmith (set `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` in `.env`): one trace per request with every agent
node, retrieval and LLM call, tagged by role and channel; UI thumbs become feedback. Prometheus text at
`/metrics`, JSON at `/metrics/summary`, audit trail in `logs/audit.jsonl`.

## Project layout
```
medbrief/   loaders (complex PDF, Word, HTML) | vision (captions) | chunking | ingest | retrieval | conditions | trials
            graph (LangGraph) | prompts | guardrails | rbac + roles.yaml | service | api | cli | observability
data/       generate_data.py, raw/ (sources), extracted/ (Markdown, images, captions, extraction report)
eval/       datasets/, run_eval.py, ragas_eval.py, langsmith_eval.py, results/
tests/      extraction contract + workflow + API tests
ui/         Streamlit app        docs/  DESIGN.md, pitch slide
```
