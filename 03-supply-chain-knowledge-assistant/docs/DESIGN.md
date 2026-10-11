# Supply Chain Knowledge Assistant - Design Document

Portfolio prototype on synthetic data. Companion: [README](../README.md), [slides](Supply_Chain_Knowledge_Assistant.pptx).

## 1. Problem and goals
Supply-chain, quality and regulatory teams need answers from controlled documents in many formats - SOPs (PDF),
deviation reports (Word), supplier status (HTML), lot data (CSV) - and much of the critical content sits in
**figures**: decision flowcharts, network maps, data-logger charts. Access is regulated (confidential deviations
must not reach partners). Goals: accurate cited answers, summaries and search across all formats including figures,
behind REST APIs for enterprise integration, with clearance-based access and no medical or disposition advice.

## 2. Architecture
```
Sources (PDF, DOCX, HTML, MD, CSV)
  -> loaders: extract to Markdown + metadata; images extracted (PyMuPDF / python-docx) with position markers
  -> vision captions (gemma3:4b via Ollama REST, cached by SHA-256)
  -> structure-aware chunker (text | table | mixed | image | record) -> nomic-embed-text -> ChromaDB
REST API :8003 / Streamlit :8503 / CLI
  -> LangGraph workflow: guard_input -> classify_task -> authorize -> retrieve (clearance filter) -> grade
     -> generate (versioned prompt templates; llama3.2 via Ollama REST) -> verify
  -> LangSmith, /metrics, audit log
```

### Why a single agent
One knowledge domain, three tasks (QA, summarise, search). Routing between tasks is deterministic (prefix rules
plus explicit API endpoints), so a multi-agent design would add LLM calls and nondeterminism without new
capability. Search needs no LLM; QA and summaries use one call each.

## 3. Extraction and image handling
| Format | Library | Structure recovered |
|---|---|---|
| PDF | pdfplumber + PyMuPDF | page cut into horizontal strips around tables and images to keep reading order; headings from font size (>= 1.15x body); ruled tables -> Markdown; metadata line (`Document ID / Revision / Classification`) parsed; wrapped lines re-joined |
| Word | python-docx | body walked in order; heading styles -> `#`; tables -> Markdown; inline pictures (`a:blip`) extracted at their position |
| HTML | BeautifulSoup | headings, paragraphs, lists, tables |
| Markdown | - | as is |
| CSV | csv | one `record` chunk per row |

**Image pipeline**: each extracted image (min 120x120 px) is saved to `data/extracted/images/<doc>_p<page>_img<n>.png`
and replaced in the Markdown by `[[IMAGE:<id>]]`. The vision model is prompted to (1) transcribe all text in the
figure exactly, then (2) describe the flow / relationships / numbers. Captions are cached in
`data/extracted/captions.json` keyed by the image hash, so re-ingestion does not re-caption (8.5 minutes for 3
figures on 2 CPU threads). At chunking time each marker becomes an `image` chunk under the section heading
where the figure appeared, with `image_id` and `image_path` metadata so the UI shows the figure and the API
serves it (`GET /images/{id}`, clearance-checked).

Observed caption quality (gemma3:4b): text transcription exact for all three figures; descriptions mostly
right but one merges two flowchart branches and the network map caption does not link lane L3 to the East Hub
(lines are unlabelled). The transcription part carries the facts; a stronger vision model would improve the
descriptions.

## 4. Chunking
- Never cross a section; tables kept whole up to 2,500 characters (larger tables split by rows with the header
  repeated); 800-character target with 100 overlap only for long paragraphs; contextual header
  `Title (doc_id) > Section` on every chunk.
- Result: 50 chunks - 14 text, 2 table, 1 mixed, 3 image, 30 record.
- Metadata: doc_id, title, section, content_type, classification, revision, source file, image path / lot ID.

## 5. Retrieval, prompts and generation
- Hybrid vector + BM25 (RRF); **classification filter applied before ranking**; exact lookup of `LOT-` IDs in
  the question against CSV records.
- Versioned `ChatPromptTemplate`s (`supplykb/prompts.py`): `qa/v1` (cite excerpts, copy numbers / IDs exactly,
  refuse medical advice, say when not covered) and `summarize/v1` with `brief`, `detailed`, `executive` styles.
- Models are called over REST: Ollama's HTTP API for llama3.2 and gemma3:4b; the assistant itself is a REST
  service (`/ask`, `/summarize`, `/search`, `/documents`, `/images/{id}`).

## 6. Roles and access control
| Role | Clearance | Tasks |
|---|---|---|
| supply_planner | internal | qa, search, summarize |
| quality_assurance | confidential | qa, search, summarize |
| regulatory_affairs | confidential | qa, search, summarize |
| logistics_partner | public | qa, search |

Clearance levels: public < internal < confidential. Enforced as a retrieval filter (restricted text never
reaches the prompt), in `authorize` for summaries, and on `/documents` and `/images/{id}`.

## 7. Guardrails
| Guardrail | Behaviour |
|---|---|
| Medical / dosing advice | refused (supply-chain answers only) |
| Disposition commands (release, reject, quarantine, recall) | refused - QA decides; procedures explained |
| Prompt injection, attempts to force restricted documents | blocked |
| PII | emails / phones redacted |
| Output grounding | numbers and LOT- / SHP- / DEV- / SOP- / CAPA- / SUP- IDs must exist in the retrieved context |
| Nothing relevant | explicit "documents I can access do not cover this" |

## 8. Evaluation
| Metric | Result |
|---|---|
| Retrieval hit@6 / MRR (10 questions) | 1.0 / 1.0 |
| Hit rate by source type: text / table / image / record | 1.0 / 1.0 / 1.0 / 1.0 |
| Image chunk retrieved for figure questions | 100% |
| Restricted chunks returned to `logistics_partner` | 0 |
| Guardrail precision / recall (11 cases) | 1.0 / 1.0 |
| RAGAS non-LLM context precision / recall (hybrid, k=6) | 0.888 / 0.625 |

### RAGAS sweep and the decision taken
| Mode | k=3 | k=6 | k=10 (F1) |
|---|---|---|---|
| vector | 0.599 | 0.731 | 0.758 |
| BM25 | 0.576 | 0.692 | 0.735 |
| hybrid | 0.633 | 0.734 (current) | 0.752 |

The optimiser recommends hybrid k=10 (+0.018 F1). It was **not applied**: context recall here is measured
against every chunk of the reference document (a strict reference), and 10 chunks increase prompt length -
and CPU latency - by ~60%. Apply it when running on a GPU or Bedrock.

### LLM-judged RAGAS (2 end-to-end answers, CPU-capped llama3.2 judge)
| Question | LLM context recall | Response groundedness | Faithfulness | Latency |
|---|---|---|---|---|
| Which packaging configuration is used for lane L2? | 1.0 | 0.75 | judge failed | 59 s |
| How often does the data logger record temperature? | 1.0 | 0.75 | judge failed | 45 s |

The 3B judge cannot produce RAGAS faithfulness's structured statement decomposition (InstructorRetryException);
the simpler `ResponseGroundedness` rating works with it. Use a stronger judge (`RAGAS_JUDGE_PROVIDER=openai` or
Bedrock) for faithfulness in CI.

## 9. Monitoring
LangSmith traces (role / channel tags, feedback), `/metrics` (`supplykb_requests_total{intent,role,outcome}`,
latency histogram, guardrail blocks), `/metrics/summary`, `logs/audit.jsonl`.

## 10. Tech stack and limitations
pdfplumber, PyMuPDF, python-docx, BeautifulSoup, Pillow (synthetic figures), LangGraph, LangChain prompt
templates, Ollama (llama3.2, nomic-embed-text, gemma3:4b), ChromaDB, FastAPI, Streamlit, LangSmith, RAGAS,
pytest (19 tests). Limitations: scanned PDFs need OCR; chart data series are described, not extracted;
captions from a 4B vision model can blur branch logic.
