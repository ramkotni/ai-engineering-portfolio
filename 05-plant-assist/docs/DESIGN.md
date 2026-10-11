# PlantAssist - Design and Implementation

Technical design for the PlantAssist prototype: a routed RAG assistant that answers manufacturing
floor-supervisor questions from safety procedures, maintenance manuals and quality control standards.

Companion material: [README](../README.md) (setup, run, deploy) and
[PlantAssist_Architecture.pptx](PlantAssist_Architecture.pptx) (slides).

---

## 1. Goals and requirements

| Requirement | How the design meets it |
|---|---|
| Route each question to the right documentation (safety, maintenance, quality - or several) | LLM router with typed output + deterministic routing policy; one vector collection per source |
| Accurate answers | Hybrid retrieval, relevance gate, answer-only-from-excerpts prompt, numeric grounding check, LLM verifier |
| Traceable answers | Every fact cites `[n]` -> document ID, revision, section path |
| Safety first | Emergency detection with a fixed banner; hands-on maintenance always pulls lockout/tagout and PPE; requests to defeat protections are refused |
| Never guess | Relevance gate + corrective rewrite; if still nothing relevant, escalate to the document owner |
| Runs on a laptop, deploys to AWS | Ollama locally; Bedrock (Claude + Titan) by configuration only |
| Measurable | Labelled evaluation sets, offline metrics, LangSmith experiments, supervisor feedback |

Non-goals of the prototype: multi-turn conversation, user authentication, document authoring or
approval workflow, OCR of scanned documents.

**Users:** production floor supervisors (primary), maintenance technicians, quality engineers, EHS managers and
on-site contractors (safety procedures only) - see "Sample roles" in section 10 and the
[README](../README.md#who-uses-it).

## 2. End-to-end architecture

```
                       OFFLINE INGESTION                                       ONLINE QUESTION ANSWERING
 data/docs/<source>/*.md|docx|pdf                              CLI / FastAPI / Streamlit / AgentCore
          |                                                                    |
   extract (loaders.py)  -> normalised Markdown + metadata           PlantAssistant.ask()  (service.py)
          |                                                                    |
   structure-aware chunking (chunking.py)                         LangGraph StateGraph (graph.py, nodes.py)
          |                                                         analyze_query  <- input guardrails
   contextual header + metadata (ingest.py)                         route_question <- LLM router + policy
          |                                                         retrieve x N   <- Send() fan-out
   embed (nomic-embed-text | Titan v2)                              grade_documents / rewrite_query
          |                                                         generate       <- cited, excerpts only
   Chroma: safety_procedures | maintenance_manuals |                check_grounding <- output guardrails + LLM verifier
           quality_standards  (cosine, fingerprinted)               finalize | no_answer | out_of_scope | guardrail_block
                                                                               |
                                                     audit log (JSONL)  +  LangSmith traces / feedback
```

Module responsibilities:

| Layer | Module | Responsibility |
|---|---|---|
| Config and models | `config.py` | All settings from env / `.env` (providers, chunking, thresholds, guardrails, monitoring) |
| | `llm.py` | Chat + embedding factories for Ollama or Bedrock; `structured()` picks JSON-schema (Ollama) or tool calling (Bedrock); Bedrock Guardrail config |
| | `sources.py` | Source registry: description (router prompt), keywords (fallback router), answer rules, escalation contact |
| Knowledge | `loaders.py` | Extraction: Markdown / Word / PDF -> normalised Markdown + metadata |
| | `chunking.py` | Structure-aware chunking (sections, tables, size limits) |
| | `ingest.py` | Builds one Chroma collection per source; staleness detection |
| | `retrieval.py` | Hybrid retriever (vector + BM25, reciprocal rank fusion) |
| Orchestration | `router.py` | `RouteDecision` schema, LLM router, keyword fallback, `plan_retrieval()` policy |
| | `guardrails.py` | Deterministic input and output guardrails |
| | `state.py`, `nodes.py`, `graph.py` | LangGraph state, node functions, wiring |
| Interfaces | `service.py`, `cli.py`, `api.py`, `ui/streamlit_app.py`, `agentcore_app.py` | One entry point (`ask`, `feedback`) used by every channel |
| Operations | `observability.py`, `eval/`, `tests/` | Audit log, LangSmith, evaluation, tests |

## 3. Key design decision: one agentic workflow, not multi-agent

**Decision.** PlantAssist is a single LangGraph `StateGraph`. The LLM is used at three decision
points - route, generate, verify - while routing policy, retrieval, grading and guardrails are
deterministic code. The three source branches run in parallel through LangGraph `Send()`, but they
are retrievers, not autonomous agents.

**Alternatives considered.**

| Option | Pros | Cons |
|---|---|---|
| **Single agentic workflow (chosen)** | Same reviewed path for every safety-critical answer; 2-3 LLM calls per question; every branch unit-testable with fakes; easy to audit | Less flexible if domains need very different tools |
| Supervisor + domain agents (multi-agent) | Each domain can own tools (CMMS, MES, SDS DB) and reasoning loops | 6-12 LLM turns per question (minutes on CPU); non-deterministic paths; harder to guarantee "LOTO is always included"; harder to test |
| Single ReAct agent with a search tool per source | Simple to write | The model decides whether to look at safety docs - the safety policy becomes a prompt suggestion instead of code |

**Why.** The domains differ by *document set*, not by *skill or tool*, so separate agents add
cost and variance without improving routing. Safety requirements (always pull lockout/tagout for
hands-on work, fixed emergency numbers) must be enforced in code, not left to model judgement.

**Upgrade path.** When a domain needs its own tools (e.g. "open a work order" in the CMMS, "look up
the lot in the MES"), turn that `retrieve` branch into a LangGraph sub-graph agent; `route_question`
becomes the supervisor. The state, guardrails, evaluation and monitoring stay unchanged.

## 4. Ingestion pipeline (extraction and chunking)

### 4.1 Extraction - every format becomes Markdown

All formats are converted into one normalised representation - Markdown text plus document
metadata - so a single chunker handles everything and tables survive as tables.

| Format | Library | Structure recovered | Metadata |
|---|---|---|---|
| `.md` / `.txt` | PyYAML | Native `#`/`##`/`###` headings, pipe tables, lists | YAML front matter: `doc_id`, `title`, `revision`, `owner`, `effective` |
| `.docx` | python-docx | Paragraphs and tables walked **in body order**; `Title`/`Heading 1-3` styles -> `#`/`##`/`###`; list styles -> bullets; tables -> Markdown pipe tables | Core-properties title; header lines like `Document ID: X`, `Revision: Y`, `Owner: Z` |
| `.pdf` | pdfplumber | **Reading order**: each page is cut into horizontal strips between detected tables, so text and tables stay in sequence; table areas are excluded from text to avoid duplicates. **Headings**: PDFs have no heading tags, so lines whose font is >= 1.15x the median body size become headings (largest = `#`). Wrapped lines are re-joined | PDF metadata title; same header-line parsing as Word |

Verified: the sample Word file `MM-HP-200-TS_torque_specs.docx` and its PDF rendering
(`tests/fixtures/torque_specs.pdf`) produce **identical** sections and tables
(`tests/test_chunking.py::test_docx_and_pdf_extract_same_structure`).

Limits and production options: scanned PDFs need OCR (Amazon Textract, or Docling/Unstructured with
OCR); tables with merged cells are flattened; diagrams and photos are not described (a vision model
could caption them). Images are ignored today.

### 4.2 Structure-aware chunking

Fixed-size windows cut procedures mid-step and tables mid-row, which produces chunks that are
retrieved but cannot answer the question. PlantAssist chunks by document structure
(`chunking.py`), in priority order:

1. **Never cross a section boundary.** Each chunk belongs to exactly one heading path
   (`Title > Section > Subsection`), stored as `section_path` metadata and shown in citations.
2. **Never split a table that fits** in `TABLE_MAX_CHARS` (2,500). Larger tables are split by rows
   and **every piece repeats the header row**, so each chunk is still a readable table.
3. **Pack** paragraphs, lists and steps of one section together up to `CHUNK_SIZE`; a single
   paragraph longer than `CHUNK_SIZE` is split recursively (paragraph -> line -> sentence -> word)
   with `CHUNK_OVERLAP`.
4. **Contextual header.** Every chunk is prefixed with `Title (doc_id) > Section path`, so both the
   embedding and BM25 know which document and section the text belongs to (e.g. the bare row
   "Gland retainer bolts | 210" becomes findable by "HP-200 torque").

Each chunk carries metadata: `source`, `doc_id`, `title`, `section`, `section_path`,
`content_type` (`text` / `table` / `mixed`), `chunk_index`, `revision`, `owner`, `file`.

Example table chunk (from the Word document):

```
HP-200 Torque and Fluid Specifications (MM-HP-200-TS) > Torque Specifications
Use a calibrated torque wrench (see QCS-004). ...
| Fastener | Location | Size | Torque (ft-lb) | Pattern / note |
|---|---|---|---|---|
| Gland retainer bolts | Main cylinder | M20 | 210 | Star pattern, 2 passes |
...
```

### 4.3 Chunk size - how it is configured and why

| Setting | Default | Unit | Rationale |
|---|---|---|---|
| `CHUNK_SIZE` | 900 | characters (~225 tokens) | One procedure section or a handful of steps: specific enough to rank well, large enough to keep a procedure together. Well under the embedding models' input limits (nomic-embed-text 2,048 tokens context in Ollama; Titan v2 8,192) |
| `CHUNK_OVERLAP` | 120 | characters | Only applied when one paragraph exceeds `CHUNK_SIZE`; section-based chunks need no overlap because sections are self-contained |
| `TABLE_MAX_CHARS` | 2,500 | characters | Spec tables are answered row-by-row but must keep their header; up to ~2.5k chars a table stays whole |
| `TOP_K` | 5 | chunks per routed source | Enough recall for multi-section answers |
| `MAX_CONTEXT_CHUNKS` | 6 | chunks to the LLM | ~2.5k-token prompt: fits a 4,096-token local context with room for the answer |

Resulting corpus (13 documents, 3 sources): **71 chunks**, average ~400 characters, largest 1,022
(the PPE matrix table, kept whole).

Tuning: change the values in `.env`. The index stores a **fingerprint** (embedding model, chunker
version, chunk settings); the API, UI and AgentCore entrypoint rebuild the index automatically when
it no longer matches. Use the evaluation (retrieval hit rate, MRR, fact recall) to compare settings.

### 4.4 Embedding and indexing

- **One Chroma collection per source** (`safety_procedures`, `maintenance_manuals`,
  `quality_standards`), cosine distance. Routing then maps directly to which index is searched, so a
  maintenance question can never be answered from a quality document by accident, and each content
  owner's corpus can be re-indexed independently. (Alternative: one collection with a `source`
  metadata filter - equivalent for retrieval, but less isolation.)
- Embeddings: `nomic-embed-text` locally (with its required `search_document:` / `search_query:`
  task prefixes), Amazon Titan Text Embeddings v2 on AWS.
- Deterministic chunk IDs (`doc_id::chunk_index`); a full rebuild of 71 chunks takes ~35 s on a
  4-core CPU.

## 5. Question-answering pipeline (RAG)

```
START -> analyze_query --blocked--> guardrail_block -> END
             | ok
         route_question --out_of_scope--> out_of_scope -> END
             | Send() per target source (parallel)
         retrieve x N -> grade_documents --nothing relevant, 1st time--> rewrite_query -> route_question
                              |            --nothing relevant again--> no_answer (escalate) -> END
                          generate -> check_grounding --fails, attempts left--> generate
                                              | passes / no attempts left
                                          finalize -> END
```

| Step | Node | What happens |
|---|---|---|
| 1 | `analyze_query` | Input guardrails (length, prompt injection, unsafe request, PII redaction); emergency detection (`fire`, `injury`, `spill`...) |
| 2 | `route_question` | `llm.with_structured_output(RouteDecision)` -> `{primary_source, secondary_sources, confidence, rationale}`; keyword router if the LLM fails. `plan_retrieval()` policy: confidence < 0.6 -> search every source; confident out-of-scope -> decline; emergency -> safety mandatory; hands-on maintenance -> add a LOTO/PPE-focused safety search |
| 3 | `retrieve` (x N, parallel) | Hybrid search in that source's collection: vector (cosine) + BM25, merged by reciprocal rank fusion (k = 60). Results merge through the `merge_documents` reducer |
| 4 | `grade_documents` | De-duplicate; keep chunks with cosine >= 0.55; keep the best chunk of policy-mandated sources; interleave sources so one cannot crowd out another; max 6 |
| 5 | `rewrite_query` | Once, if nothing relevant: the LLM rewrites the question in plant terminology, then it is re-routed |
| 6 | `generate` | Prompt: answer only from numbered excerpts, cite `[n]`, copy numbers exactly, say "the documentation does not cover this" otherwise; per-source answer rules from the registry |
| 7 | `check_grounding` | Output guardrails (citations, numeric grounding, unsafe advice), then the optional LLM verifier; on failure regenerate once with the list of unsupported claims |
| 8 | terminal nodes | `finalize` (emergency banner, caveat if still unverified, withhold unsafe answers), `no_answer` (escalation contact), `out_of_scope`, `guardrail_block` |

Why hybrid retrieval: small embedding models compress similarity (on this corpus, relevant chunks
score 0.62-0.85 and unrelated ones 0.48-0.65). BM25 fixes ranking for exact plant vocabulary
(part numbers, alarm codes, "gland retainer"); cosine stays the absolute relevance signal for the
gate. Measured example: "torque for the gland retainer bolts" ranked #2 with vector-only search and
#1 with hybrid.

Every loop is bounded (1 rewrite, `MAX_GENERATION_ATTEMPTS` generations), so the graph always
terminates with an answer, a decline, a block or an escalation.

## 6. Guardrails

Layered, **deterministic first**: rules run on every request at negligible cost and keep working
when the LLM verifier is switched off on a CPU-only laptop.

| Layer | Guardrail | Implementation | On trigger |
|---|---|---|---|
| Input | Size limit | `MAX_QUESTION_CHARS` (1,000) | Block with a "ask one specific question" message |
| Input | Prompt injection | Regex for "ignore previous instructions", "reveal system prompt", "you are now...", jailbreak | Block before any LLM call |
| Input | Unsafe request | Requests *how to* defeat a protection: bypass/jumper/disable a light curtain, interlock, guard, e-stop...; skip lockout/PPE/permits. **Reports of a past violation are allowed** ("the interlock was bypassed by night shift, what do I do?") | Block with a fixed message citing SOP-SAF-001/003 and the EHS contact |
| Input | PII redaction | Emails and phone numbers -> `[email]`, `[phone]` (plant extensions like `ext. 5555` are kept) | Redact before the LLM, logs and LangSmith see the text |
| Routing | Scope control | Router `out_of_scope` with confidence >= 0.6 | Polite decline, no retrieval |
| Routing | Safety-first policy | Emergency language or hands-on maintenance -> mandatory safety search | Lockout/tagout and PPE always in context |
| Retrieval | Relevance gate | Cosine >= 0.55 | Rewrite once, then escalate - never answer from weak context |
| Output | Citation validity | Remove `[n]` that point to non-existent excerpts; flag answers with no citations | Cleaned answer; issue recorded |
| Output | **Numeric grounding** | Every number in the answer (torques, pressures, limits, intervals, extensions) must appear in the excerpts or the question | Regenerate with feedback; caveat if still failing |
| Output | Unsafe advice | Answer suggests skipping/bypassing a protection | Answer withheld, replaced by a safety message |
| Output | LLM verifier | Second LLM pass lists unsupported claims (`GROUNDING_CHECK`) | Regenerate once; caveat if still unverified |
| Response | Emergency banner | Fixed text with ext. 5555 / 911, prepended by code | Always shown first for emergencies |
| Platform (AWS) | Amazon Bedrock Guardrails | `BEDROCK_GUARDRAIL_ID` -> `guardrail_config` on every Claude call | Content filters, denied topics, PII masking managed in AWS |

Measured: 16/16 guardrail cases correct (8 unsafe/injection blocked, 8 legitimate safety questions
allowed - block precision 1.0, recall 1.0). Unit tests: `tests/test_guardrails.py`.

Why rules plus an LLM verifier rather than an LLM alone: the 3B local model's verifier flagged
almost every answer (including correct ones), while the numeric rule is exact for the facts that
matter most on the floor - numbers. With Claude on Bedrock both layers are enabled.

## 7. Evaluation

### 7.1 Datasets
- `eval/routing_dataset.jsonl` - 28 labelled questions: expected source, acceptable documents,
  expected key facts (e.g. "650" for the cylinder mounting bolt torque), including table-only
  questions and off-topic questions.
- `eval/guardrail_dataset.jsonl` - 16 cases: unsafe requests and injections that must be blocked,
  and look-alike legitimate safety questions that must pass.

### 7.2 Metrics

| Area | Metric | Definition |
|---|---|---|
| Routing | Accuracy | Predicted primary source = label (LLM router and keyword fallback reported separately) |
| Retrieval | Hit@k | An acceptable document is among the chunks retrieved for the routed sources |
| Retrieval | MRR | Mean of 1 / rank of the first acceptable document |
| Guardrails | Block precision / recall | On the guardrail set |
| Answers (`--full`) | Answered rate | In-scope questions answered (not escalated) |
| | Expected doc cited | An acceptable document appears in the citations |
| | Fact recall | Share of expected key facts present in the answer |
| | Citation validity / numeric grounding | From the output guardrails |
| | Latency p50 / p95 | End to end |

### 7.3 How to run

```powershell
python -m eval.run_eval --no-llm   # routing (keyword), retrieval, guardrails - no chat-model calls, ~20 s
python -m eval.run_eval            # + LLM router accuracy
python -m eval.run_eval --full     # + end-to-end answer metrics (slow on CPU; fast on Bedrock)
python -m eval.langsmith_eval      # same questions as a LangSmith experiment with evaluators
```

### 7.4 Current results (llama3.2 / nomic-embed-text, 4-core CPU)

| Metric | Result |
|---|---|
| Retrieval hit@5 | **100%** (26/26 in-scope) |
| Retrieval MRR | **0.974** |
| Guardrail block precision / recall | **1.0 / 1.0** (16 cases) |
| Keyword fallback routing accuracy | 82% (23/28) - its misses still retrieve the right document because low confidence fans out to every source |
| Live LLM routing (4 demo questions) | 4/4 correct |

The LLM-router and full answer runs are left to `run_eval` / `--full` because they take minutes per
question on this CPU; on Bedrock they run in a few minutes in total.

### 7.5 Using evaluation as a regression gate
Run `--no-llm` in CI on every change to chunking, retrieval or guardrails (fast, deterministic);
run `--full` or the LangSmith experiment before changing the model, prompts or thresholds, and
compare experiments side by side in LangSmith.

## 8. Monitoring and observability

### 8.1 LangSmith
Enable in `.env`: `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`, `LANGSMITH_PROJECT=plant-assist`.

- **Tracing**: every graph run is traced automatically by LangChain/LangGraph - each node, the
  router's structured output, every retriever call, prompts, token usage and latency.
- **Run metadata**: `run_name=plant_assist.ask`, tags `plant-assist`, `provider:<ollama|bedrock>`,
  `channel:<api|streamlit|cli|eval>`, metadata with model IDs. A known `run_id` is generated per
  question and returned to the client.
- **Feedback**: supervisor "Helpful / Not helpful" (Streamlit buttons, `POST /feedback`) is
  attached to the run as `supervisor_rating`.
- **Experiments**: `eval/langsmith_eval.py` uploads the labelled set once and scores every run with
  `route_correct`, `expected_doc_cited`, `fact_recall`, `numbers_grounded`.
- **Privacy**: `LANGSMITH_HIDE_INPUTS=true` / `LANGSMITH_HIDE_OUTPUTS=true` keep questions and
  document text out of LangSmith (structure and timings are still traced); PII is redacted before
  tracing in any case. For regulated plants use self-hosted LangSmith.

Suggested dashboards and alerts: p95 latency; share of `no_answer`, `blocked` and `grounded=false`
outcomes; negative-feedback rate per source; router fallback rate (`method=keyword-fallback`).

### 8.2 Local audit log
`logs/audit.jsonl` (configurable with `AUDIT_LOG_PATH`) records one line per question - timestamp,
run ID, redacted question, route, sources searched, documents cited, guardrail results, outcome,
latency - plus one line per feedback. It is the plant's own record of what the assistant said,
independent of any SaaS, and works offline.

## 9. Technology stack

| Layer | Technology | Version tested | Why |
|---|---|---|---|
| Language | Python | 3.12.5 | Ecosystem for LLM tooling |
| Orchestration | LangGraph | 1.2.14 | Explicit state machine: conditional edges, parallel `Send()`, bounded loops, reducers |
| LLM framework | LangChain core | 1.6.9 | Model abstraction, structured output, messages, text splitters |
| Local models | Ollama + `llama3.2` (3B) + `nomic-embed-text` | Ollama 0.40.2 | Free, private, runs on a laptop CPU |
| Cloud models | Amazon Bedrock: Claude (chat), Titan Text Embeddings v2 | langchain-aws 1.8.1 | Managed, data stays in the AWS account, Guardrails available |
| Vector store | Chroma (persistent) | 1.5.9 | Embedded, zero-ops for a prototype; per-source collections |
| Keyword search | In-process BM25 | - | Exact plant vocabulary; no extra service for a small corpus |
| Extraction | PyYAML, python-docx, pdfplumber | 6.0.3 / 1.2.0 / 0.11.10 | Front matter, Word structure, PDF text + tables |
| Config | pydantic-settings, python-dotenv | 2.15.0 / 1.2.4 | Typed settings from env / `.env` |
| API / UI | FastAPI + Uvicorn, Streamlit | 0.143.0 / 1.65.0 | REST for integration; quick supervisor UI |
| AWS runtime | Bedrock AgentCore Runtime (`bedrock-agentcore`), or App Runner / ECS via Docker | 1.24.1 | Managed agent hosting or a plain container |
| Monitoring | LangSmith + JSONL audit log + `/metrics` | 0.14.7 | Traces, feedback, experiments; offline audit trail |
| Testing | pytest (48 unit + 3 integration), ruff | 9.1.1 | Fakes for LLM and retrievers; no model needed for unit tests |
| Slides | pptxgenjs (Node) | 3.12.0 | Deck generated from code (`deck/build_deck.js`) |

## 10. Security and privacy

### Sample roles (portfolio version)
`plant_assist/roles.yaml`, API key -> role. A role lists the documentation sources it may search; **safety
procedures are always searchable** (safety-first). After routing, targets the role may not search are removed:

| Role | Sources |
|---|---|
| floor_supervisor | safety, maintenance, quality |
| maintenance_technician | safety, maintenance |
| quality_engineer | safety, quality |
| ehs_manager | safety, maintenance, quality |
| contractor | safety |

- All targets removed -> `access_denied` terminal node (`outcome: denied`).
- Some removed -> the answer is produced from the allowed sources and carries a note that some documentation
  was not available for the role (e.g. a contractor asking how to replace a seal gets the LOTO requirements).
- Metrics: `plant_assist_role_restricted_total{role}`; `GET /metrics` also exposes requests by primary source,
  role and outcome, guardrail blocks, router fallbacks, safety alerts and a latency histogram.

### RAGAS (portfolio version)
`eval/ragas_eval.py` evaluates retrieval given the correct source with non-LLM RAGAS context precision /
recall, sweeps retrieval mode (vector / BM25 / hybrid) x top_k, and optionally runs LLM-judged faithfulness,
response groundedness and context recall (`--llm N`, with the CPU-capped judge model). Results:
`eval/results/ragas_report.json`.

| Mode (F1 of context precision / recall) | k=3 | k=5 | k=8 |
|---|---|---|---|
| vector | 0.655 | 0.842 | 0.893 |
| BM25 | 0.603 | 0.774 | 0.853 |
| hybrid | 0.661 | 0.817 (previous) | **0.891** (applied) |

Decision: `TOP_K` raised from 5 to 8 (context recall 0.70 -> 0.84, precision 0.97 -> 0.95). This has no
prompt-length cost because grading still passes at most `MAX_CONTEXT_CHUNKS` = 6 excerpts to the LLM; it gives
the grader more candidates. Vector-only k=8 scored 0.002 higher (noise); hybrid is kept for exact codes.

Portfolio re-run (keyword routing, no LLM): routing 82% (fallback), retrieval hit 100%, MRR 0.974, guardrails
16/16.

### General
- Synthetic documents only in this repository.
- PII redaction before any LLM, log or trace; LangSmith input/output hiding available.
- Bedrock keeps prompts and documents inside the AWS account; IAM policy limited to invoking the
  Claude and Titan models (`deploy/aws/bedrock-invoke-policy.json`).
- Production: put the API behind SSO/Cognito, restrict documents by role, enable Bedrock Guardrails.

## 11. Performance and cost (observed)
- 4-core laptop CPU, llama3.2 3B: about 2-4 minutes per answer with all cores; with
  `OLLAMA_NUM_THREAD=2` Ollama is held at ~50% CPU and ~2.9 GB RAM while answering, and the model is
  unloaded 60 s after the last call (`OLLAMA_KEEP_ALIVE=60`).
- LLM calls per question: 2 (route + generate) with the LLM verifier off, 3 with it on, up to 5
  with one regeneration.
- On Bedrock, expect seconds per answer; cost is per token (roughly 3k input + 0.5k output tokens
  per LLM call with 6 excerpts).

## 12. Testing strategy
- **Unit (44, no model or index)**: router policy, keyword router, BM25; chunking (sections, tables,
  row-split with header, size limits), Word and PDF extraction; guardrails (block/allow sets, PII,
  numeric grounding, citations, unsafe advice); graph paths with a fake LLM (repair -> safety added,
  emergency banner, rewrite -> escalation, out-of-scope, blocked request, invented number ->
  regeneration -> caveat, unsafe answer withheld); audit log and feedback; evaluators.
- **Integration (opt-in)**: `RUN_INTEGRATION=1` runs real questions against Ollama/Bedrock + Chroma.
- **Evaluation**: section 7.

## 13. Limitations and roadmap
- Single-turn only -> add a LangGraph checkpointer for follow-up questions.
- Scanned PDFs and diagrams -> OCR / vision captioning.
- Chroma in-process -> OpenSearch Serverless or Bedrock Knowledge Bases with revision-aware sync from
  the document management system.
- Domain tools (CMMS work orders, MES lookups) -> per-domain sub-agents (section 3).
- Feedback loop -> curate negative-feedback questions into the evaluation set.
