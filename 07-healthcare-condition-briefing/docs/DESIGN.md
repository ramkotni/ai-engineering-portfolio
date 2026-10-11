# Condition Briefing Assistant - Design Document

Healthcare scenario: *"A health system strategy team wants a tool that generates a structured briefing for a given
medical condition, covering the current standard of care, emerging treatments in development, and key
companies/institutions involved."* Portfolio prototype on synthetic data. Companion: [README](../README.md),
[pitch slide](Condition_Briefing_Pitch.pptx).

## 1. Problem, users and goals
Strategy teams (service-line planning, partnerships, trial-site strategy) spend days assembling the same picture for
each condition: what the guideline says, what is coming in the pipeline and who is behind it. The facts sit in
**complex PDFs** (two-column guidelines with multi-page tables and figures), Word strategy briefs, HTML summaries and
trial registries.

**Users:** strategy analysts, service-line directors, executives, a physician advisor and external consultants
(public sources only) - see section 8.

| Goal | Design response |
|---|---|
| A structured briefing in minutes, same shape every time | Fixed sections; one writer call over numbered evidence |
| Correct facts from complex documents | Layout-aware PDF extraction (section 3); tables and figures become retrievable chunks |
| Counts and rankings that are right | Computed in code from the registry, never by the LLM |
| Current pipeline, not just a static file | Live ClinicalTrials.gov API v2 mode with automatic fallback |
| Appropriate access | Clearance-based retrieval filter: internal strategy docs never reach consultants |
| Safe in a clinical context | Refuses patient-specific advice; PHI redaction; numeric / ID grounding; disclaimer |

## 2. Architecture
```
Sources: complex PDF guideline | HTML guideline | Word strategy brief (internal) | trial registry CSV | ClinicalTrials.gov (live)
  -> extraction (pdfplumber + PyMuPDF / python-docx / BeautifulSoup) -> Markdown + images
  -> figure captions (gemma3:4b, cached) + caption verification
  -> structure-aware chunks (text | table | image | record) + metadata (doc_id, section, condition, classification)
  -> nomic-embed-text -> ChromaDB  (+ BM25, reciprocal rank fusion)

Request (API :8007 / Streamlit :8507 / CLI)
  -> LangGraph: guard_input -> resolve_condition -> authorize -> gather_trials
       -> [standard_of_care | pipeline | key_players | strategy]   (parallel agents)
       -> write_briefing (1 LLM call) -> verify  ->  JSON briefing + Markdown
  -> follow-up questions: retrieve -> grade -> answer -> verify
  -> LangSmith traces, /metrics, audit log
```

### Why this agent design
Four **section agents run in parallel** because each section has a different evidence source and tool:
standard of care = guideline retrieval (tables, algorithm figure); pipeline = registry analytics + the guideline's
"emerging therapies" text and chart; key players = sponsor / site aggregation; strategy = internal documents (only
for cleared roles). They are deterministic (retrieval and pandas-free Python counting), so they cost no LLM calls.
A **single writer call** then turns all evidence into prose. On a CPU, one 900-token generation is far cheaper than
one LLM call per section, and a single pass keeps the executive summary consistent with the sections.
Multi-turn agent loops (ReAct) were rejected: the plan is the same for every condition, so a fixed graph is more
predictable, testable and cheaper.

## 3. Extraction - how the complex PDF is handled
The guideline PDF (`CARD-GL-2026`, 4 pages) was generated to contain the layouts that break naive extraction.
`medbrief/loaders.py` handles each one; `python -m medbrief.loaders <file>` prints the result, and the UI's
**Extraction** tab shows it side by side with the extracted images.

| Layout problem | What naive `page.extract_text()` produces | Technique | Result on CARD-GL-2026 |
|---|---|---|---|
| Running header / footer on every page | Header and "Page 2 of 4" inside sentences and chunks | Lines in the top / bottom 8% band whose text (digits masked) repeats on >= half of the pages are removed and the page is cropped between them | 8 lines removed (2 per page) |
| Two-column body with full-width headings | Left and right column lines interleaved row by row | Page cut into horizontal strips around tables and images; in each strip every text row is full-width if a character crosses the centre gutter, otherwise it is a column row; runs of column rows are read left column then right column. Captions and large-font headings break the column flow unless text exists on both sides (two column headings side by side) | 4 two-column blocks, correct order |
| Ruled tables | Cells flattened into run-on lines | pdfplumber `find_tables()` on the ruling lines -> Markdown pipe table | 3 table fragments |
| Table continued across a page break, header row repeated | Two tables, duplicated header, "(continued)" caption | A table whose header row equals the previous table's header is merged into it; "Table N (continued)" captions removed | Table 1: 11 drug rows in one table, one header |
| Embedded figures (algorithm, chart) | Nothing - the content exists only as pixels | PyMuPDF extracts each image with its page rectangle; it is saved as PNG and a `[[IMAGE:id]]` marker is placed at its position in the text flow; the printed "Figure N." caption becomes its caption hint | 2 figures at the right place, under the right sections |
| Footnotes in small type | Mixed into the last paragraph | Text below 0.8 x body font size -> `Footnote:` lines | 2 footnotes |
| Headings | Lost | Font size >= 1.15 x median body size; the three largest sizes map to `#`, `##`, `###` | 8 headings, correct levels |
| Document metadata | Plain text | "Document ID / Revision / Classification" line parsed into metadata | doc_id, revision, classification=public |

Word (`python-docx`) walks the body in order (headings by style, tables, inline images via `a:blip` at their
position); HTML (`BeautifulSoup`) keeps headings, lists and tables. Extraction artefacts are committed for review:
`data/extracted/markdown/*.md`, `data/extracted/images/*.png`, `data/extracted/extraction_report.json`.

### Figures: vision captions and caption verification
Each figure is captioned once by `gemma3:4b` through the Ollama REST API (prompt: transcribe all text, then describe
the flow / every category and value) and cached by SHA-256 in `data/extracted/captions.json` (~25 minutes for 3
figures on 2 CPU threads; re-ingestion is instant). The caption becomes an `image` chunk under the figure's section,
so "When is CRT-D indicated?" retrieves the algorithm and "how many device programs?" retrieves the chart.

Observed quality: transcription of the pipeline chart was exact; the algorithm transcription was exact **except one
drug name - "Hydralazine" was read as "Hydrochlorothiazide"**, a different drug; the admissions-chart description said
readmission "hovers around 21.4%" when it ranged 21.4-24.8%. Mitigation in code: drug-like words in a caption
(by suffix) that appear nowhere else in the source document are flagged on the chunk -
`[Vision transcription - terms not found elsewhere in the document, verify: Hydrochlorothiazide]` - so the writer and
the reader are warned. A stronger vision model (Claude on Bedrock) or OCR + layout for figures would remove most of
these errors.

## 4. Chunking
Structure-aware (shared with the other portfolio projects): never cross a section; tables kept whole up to 2,500
characters (larger ones split by rows with the header repeated); 800-character target with 100 overlap for long
paragraphs; contextual header `Title (doc_id) > Section` on every chunk; each figure and each registry row is its own
chunk. Result: **50 chunks** - 17 text, 3 mixed, 1 table, 3 image, 26 record. Metadata: doc_id, title, section,
condition (`hfref` | `t2d` | `all`, tagged per chunk for the multi-condition strategy brief), classification,
content_type, image path, trial ID.

## 5. Retrieval and the briefing workflow
- Hybrid retrieval: nomic-embed-text vectors (with `search_document:` / `search_query:` prefixes) + BM25, fused with
  reciprocal rank fusion. **Filters are applied before ranking**: guideline doc IDs for the condition, condition tag,
  and the role's visible classifications.
- Each section agent runs several targeted queries (e.g. standard of care: treatment recommendations, algorithm and
  device thresholds, diagnosis, quality measures) and de-duplicates.
- The writer receives numbered evidence `[1]..[n]` - guideline chunks, figure captions, internal chunks and a
  **registry analysis block computed in code** (active programs, phases, modalities, late-stage list, readouts by year,
  ranked companies and institutions) - and must cite numbers. The UI and API render the deterministic tables
  (late-stage programs, companies, institutions) next to the prose.
- Follow-up questions use the same index (QA prompt template, exact lookup of `SYN-..` trial IDs).

### Live data mode
`TRIALS_SOURCE=live` (or the UI toggle) queries the **ClinicalTrials.gov API v2** for recruiting / active Phase 2-3
interventional studies of the condition and maps them to the same `Trial` schema, so pipeline and key-player
analytics work unchanged with real sponsors and sites. Any condition can then be briefed (the standard-of-care
section says when no guideline is in the knowledge base). Network failure falls back to the synthetic registry and
the briefing says so. Roles without live-data permission are downgraded to synthetic data with a note.

## 6. Prompts
Versioned `ChatPromptTemplate`s (`medbrief/prompts.py`): `briefing/v1` (fixed headings, 2-4 cited bullets each,
copy numbers and IDs exactly, no patient advice, "Not covered" when evidence is missing; style per role: analyst,
executive, clinical) and `qa/v1`. The parser tolerates model formatting (`### Heading:`, numbered lists). If the LLM
fails, an extractive briefing is produced instead of an error.

## 7. Guardrails
| Guardrail | Where | Behaviour |
|---|---|---|
| Patient-specific advice ("should my father start...", "what dose should I take") | input | refused - strategy tool, not clinical advice |
| Prompt injection, attempts to force internal documents | input | blocked |
| PHI / PII (MRN, date of birth, SSN, phone, email) | input and output | redacted before the graph runs |
| Numeric grounding | output | every number must appear in the evidence |
| Identifier grounding | output | trial and document IDs (`SYN-HF-101`, `NCT...`, `CARD-GL-2026`) must exist in the evidence |
| Second-person treatment language | output | flagged |
| Unverified vision transcription | ingestion | flagged on the chunk (section 3) |
| Disclaimer | output | always attached |

## 8. Roles
| Role | Clearance | Tasks | Live data | Style |
|---|---|---|---|---|
| strategy_analyst | internal | briefing, qa | yes | analyst |
| service_line_director | internal | briefing, qa | yes | analyst |
| executive | internal | briefing | no | executive |
| clinical_advisor | internal | briefing, qa | yes | clinical |
| external_consultant | public | briefing, qa | no | analyst |

Enforced in code: the retrieval filter (internal chunks never reach a public role's prompt), the strategy agent is
skipped for public roles, `/documents`, `/extraction` and `/images/{id}` apply the same clearance.

## 9. Evaluation
`python -m eval.run_eval` (no LLM) and `python -m eval.ragas_eval --optimize`:

| Check | Result |
|---|---|
| Extraction checks (header/footer, columns, merged table, all rows, figures, footnotes, Word image, captions) | 8 / 8 |
| Retrieval hit@6 / MRR (12 questions, one per source type) | 1.0 / 0.917 |
| Hit rate by source type: table, continued-page table row, figure, two-column text, HTML, record, Word internal, footnote | 1.0 each |
| Internal chunks returned to the public role | 0 |
| Guardrail precision / recall (14 cases incl. strategy questions mentioning doses / patients) | 1.0 / 1.0 |
| Registry analytics vs direct CSV count (active programs, modality counts, top company) | 6 / 6 |
| Unit tests | 37 passed |

### RAGAS (non-LLM context precision / recall) and the retrieval decision
| Mode | k=3 F1 | k=6 F1 | k=10 F1 |
|---|---|---|---|
| vector | 0.869 | 0.866 | 0.865 |
| BM25 | 0.924 | 0.924 | 0.930 |
| hybrid | 0.924 | **0.924 (current: precision 0.958, recall 0.892)** | 0.927 |

Vector-only retrieval is clearly worse on this corpus: questions hinge on exact drug names, trial IDs and table
labels, which BM25 matches. BM25 k=10 is 0.006 F1 higher - within noise for 12 questions - so hybrid k=6 is kept
(the vector half matters for paraphrased questions the dataset does not cover).

LLM-judged results and end-to-end briefing runs are recorded in [section 9.1](#91-end-to-end-llm-runs).

### 9.1 End-to-end LLM runs
| Run | Result |
|---|---|
| HFrEF briefing, `strategy_analyst`, first version (6 guideline chunks, 900-token cap) | answered in **600 s**; all sections filled; numbers grounded (verify: pass); but 12-bullet sections and no citation markers - the 3B model ignored both instructions |
| Same request after tuning (4 guideline chunks, 650-token cap, bullet cap, citation backfill) | **492 s**; every bullet cited (backfilled where the model omitted it); strategic section used the internal target (four-pillar rate 65% within 12 months); one bullet cut off by the token cap -> truncation trimming added |
| Repeat request, same clearance and style | **< 1 s** from the role-scoped briefing cache (24 h) |

LLM-judged RAGAS (`python -m eval.ragas_eval --llm 2`, local `llama3.2-judge` capped at 2 threads):

| Question | LLM context recall | Response groundedness | Faithfulness | Answer latency |
|---|---|---|---|---|
| Target dose of sacubitril/valsartan and recommendation class | 1.0 | 0.0 | judge failed (InstructorRetryException) | 75 s |
| When is vericiguat recommended? | 1.0 | 1.0 | 0.333 | 108 s |

Context recall is perfect; the generation-side scores from a 3B judge are noisy (it cannot reliably produce RAGAS's
structured statement decomposition), so they are recorded but not used for decisions. Use a stronger judge
(`RAGAS_JUDGE_PROVIDER=openai` or Bedrock) for faithfulness in CI.

Live mode check (no LLM): ClinicalTrials.gov returned 36 recruiting / active Phase 2-3 HFrEF studies and 40 for
atrial fibrillation (a condition outside the catalogue); companies and academic sponsors were ranked as for the
synthetic registry.

## 10. Monitoring
LangSmith tracing (tags: role, channel, provider; feedback from the UI's thumbs), Prometheus-format `/metrics`
(`medbrief_requests_total{intent,role,outcome}`, latency histogram, guardrail blocks, output flags, feedback),
`/metrics/summary`, `logs/audit.jsonl`.

## 11. Tech stack
Python 3.12, LangGraph 1.2 (parallel fan-out / join), LangChain core 1.6 (prompt templates, messages),
langchain-ollama, Ollama (`llama3.2`, `nomic-embed-text`, `gemma3:4b`), ChromaDB 1.5 + BM25, pdfplumber 0.11,
PyMuPDF 1.28, python-docx 1.2, BeautifulSoup 4.15, httpx (ClinicalTrials.gov), FastAPI + Uvicorn, Streamlit,
LangSmith, RAGAS 0.4.3, pytest, ruff. Amazon Bedrock by configuration.

## 12. Trade-offs and limitations
- Synthetic sources; clinical content is simplified and not clinical guidance.
- The 3B local model writes adequate but plain prose on CPU in minutes; Bedrock (Claude) would cut latency to seconds
  and improve synthesis - the code path exists (`LLM_PROVIDER=bedrock`).
- Scanned PDFs need OCR; rotated pages and tables without ruling lines need a layout model (e.g. Textract, Docling).
- Vision captions can misread small text (observed) - flagged, not corrected.
- Live mode uses ClinicalTrials.gov only; FDA approvals, conference abstracts and news would complete the pipeline view.

Next steps: guideline library per condition, Bedrock + Claude for writing and figure reading, scheduled refresh of
briefings with change highlights, export to the health system's document template.
