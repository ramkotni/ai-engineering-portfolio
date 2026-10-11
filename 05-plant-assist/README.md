# 05 - PlantAssist: routed RAG for manufacturing floor supervisors

> Portfolio prototype on **synthetic data** (fictional plant, equipment and numbers).

| | |
|---|---|
| **Test URLs** | API **http://localhost:8005/docs** - UI **http://localhost:8505** - metrics **http://localhost:8005/metrics** |
| **Roles** | `floor_supervisor`, `maintenance_technician`, `quality_engineer`, `ehs_manager`, `contractor` (see below) |
| **Evaluation** | `eval/run_eval.py`, `eval/ragas_eval.py` (RAGAS), `eval/langsmith_eval.py` |

PlantAssist answers floor-supervisor questions from the **right** plant documentation -
**safety procedures**, **maintenance manuals** or **quality control standards** - and cites
the document, revision and section behind every fact.

Built with **Python, LangGraph and LangChain**. Runs locally on **Ollama**; moves to
**AWS Bedrock** (Claude + Titan embeddings) by changing environment variables only.

- **Design document** (end-to-end pipeline, chunking, guardrails, evaluation, monitoring, decisions, tech stack): [docs/DESIGN.md](docs/DESIGN.md)
- **Architecture deck**: [docs/PlantAssist_Architecture.pptx](docs/PlantAssist_Architecture.pptx)
- The 13 documents in `data/docs/` (12 Markdown + 1 Word) are **synthetic** (fictional plant, equipment and numbers) - do not use them as real procedures.

Features at a glance:

| Feature | Where |
|---|---|
| LLM routing to safety / maintenance / quality, with a safety-first policy | `router.py` |
| Extraction of Markdown, Word and PDF (headings + tables) into one normalised form | `loaders.py` |
| Structure-aware chunking: per section, tables kept whole, contextual headers | `chunking.py` |
| Hybrid retrieval (vector + BM25) over one index per source | `retrieval.py` |
| Guardrails: prompt injection, unsafe requests, PII redaction, citation + numeric grounding, unsafe-advice filter, Bedrock Guardrails | `guardrails.py` |
| Evaluation: routing, retrieval hit@k / MRR, guardrails, answer fact recall; LangSmith experiments | `eval/` |
| Monitoring: LangSmith tracing + supervisor feedback, local JSONL audit log | `observability.py` |

---

## 1. Business use case

| | |
|---|---|
| **Users** | Floor supervisors, on a tablet or PC at the line |
| **Problem** | Answers live in three document sets owned by three teams (EHS, Maintenance, Quality). Supervisors know the question, not which binder holds the answer. A maintenance answer that omits lockout/tagout is a safety risk. |
| **What PlantAssist does** | Routes each question to the right source(s), answers only from those documents, cites every fact, adds safety prerequisites to hands-on work, and escalates instead of guessing. |
| **Pilot targets** | Time to the right procedure in seconds; 100% of answers cited (audit trail); fewer routine calls to engineers. These are targets to measure in a pilot, not prototype results. |

Example scenarios:

| Situation | PlantAssist |
|---|---|
| HP-200 press breakdown - "How do I replace the main cylinder seal?" | Seal-kit steps from the maintenance manual **plus** lockout/tagout from the safety SOP, all cited |
| "About 10 gallons of solvent spilled near line 3" | Deterministic emergency banner (ext. 5555), then the major-spill response |
| "Eight points in a row above the X-bar center line" | Western Electric rule from the SPC standard and the reaction plan |
| "What's on the cafeteria menu?" | Polite decline - no retrieval, no generated answer |

## 2. Is this multi-agent?

**No - it is an agentic workflow, by design.** One LangGraph `StateGraph` uses an LLM at three
decision points (route, generate, verify); routing policy, retrieval and grading are deterministic
code. The three source branches run in parallel via LangGraph `Send()` - they are retrievers, not
autonomous agents.

Why: a safety-critical answer should follow the same reviewed path every time; 3 LLM calls per
question instead of 6-12 agent turns matters on a CPU; and the domains are document sets, not
different tools. **Upgrade path:** when domains need their own tools (CMMS work orders, MES
lookups, SDS database), each `retrieve` branch becomes a sub-agent subgraph and `route_question`
becomes the supervisor.

## 3. How routing works

```
question
  -> analyze_query      emergency regex (fire, injury, spill ...) -> safety_alert
  -> route_question     LLM returns a typed RouteDecision {primary_source, secondary_sources, confidence, rationale}
                        (keyword router takes over if the LLM fails)
                        plan_retrieval() applies plant policy:
                          confidence < 0.6           -> search every source
                          confident out_of_scope     -> decline, no retrieval
                          emergency language         -> safety always searched + fixed banner
                          hands-on maintenance task  -> add safety search with a LOTO/PPE-focused query
  -> dispatch           one Send("retrieve", target) per source -> parallel branches
  -> retrieve x N       each branch searches ONLY its own Chroma collection (hybrid BM25 + vector)
  -> grade_documents    cosine >= 0.55 gate, keep policy-mandated chunks, interleave sources (max 6)
       |-> rewrite_query -> route_question   (once, if nothing relevant)
       |-> no_answer                          (escalate to the document owner's extension)
  -> generate           cited answer from excerpts only
  -> check_grounding    LLM verifier; regenerate once with feedback, else add a caveat
  -> finalize
```

Real routing decisions from the live run (llama3.2, CPU):

| Question | Router | Policy | Collections searched |
|---|---|---|---|
| Replace the HP-200 cylinder seal | maintenance, 0.95 | hands-on -> + safety (LOTO query) | maintenance_manuals, safety_procedures |
| 10 gallons of solvent spilled | safety, 0.99 | emergency banner | safety_procedures |
| 8 points above the X-bar center line | quality, 0.90 | - | quality_standards |
| Cafeteria menu | out_of_scope, 0.95 | decline | none |

Print the compiled graph as Mermaid: `python -m plant_assist.graph`

## 4. Code walkthrough

Read in this order: `sources.py` -> `router.py` -> `nodes.py` -> `graph.py` -> `service.py`.

```
plant_assist/
  config.py      Settings from env / .env (providers, thresholds, Ollama resource limits)
  llm.py         get_chat_model() / get_embeddings(): Ollama or Bedrock; structured() picks json_schema vs tool calling
  sources.py     Source registry: description (router prompt), keywords (fallback), answer rules, escalation contact
  loaders.py     Extraction: .md (front matter) / .docx (heading styles, tables) / .pdf (font-size headings, tables in reading order) -> Markdown
  chunking.py    Structure-aware chunking: never cross a section, keep tables whole (split by rows with header if huge), contextual header
  ingest.py      Builds one Chroma collection per source; index fingerprint -> automatic rebuild when model/chunking changes
  retrieval.py   HybridSourceRetriever: Chroma cosine + in-memory BM25, fused with reciprocal rank fusion
  router.py      RouteDecision schema, llm_route(), keyword_route(), plan_retrieval() policy
  guardrails.py  Input (injection, unsafe request, PII, length) and output (citations, numeric grounding, unsafe advice) checks
  state.py       GraphState TypedDict; merge_documents reducer for parallel fan-in (None = reset)
  nodes.py       The 11 node functions + conditional-edge functions; deps injected for testing
  graph.py       StateGraph wiring only
  service.py     PlantAssistant.ask() / feedback() - single entry point for every interface
  observability.py  LangSmith run config + feedback; JSONL audit log
  cli.py         ask / chat / ingest
  api.py         FastAPI: POST /ask, POST /feedback, GET /health
ui/streamlit_app.py   supervisor demo UI (with Helpful / Not helpful feedback)
agentcore_app.py      Amazon Bedrock AgentCore Runtime entrypoint
data/docs/            synthetic docs: safety/ maintenance/ quality/ (Markdown + one Word file with tables)
data/make_sample_docs.py  regenerates the sample Word document
tests/                44 unit tests (fake LLM + fake retrievers, no model needed) + 3 opt-in integration tests
eval/                 routing_dataset (28) + guardrail_dataset (16) + run_eval.py + langsmith_eval.py
docs/                 DESIGN.md, PlantAssist_Architecture.pptx
deck/                 build_deck.js -> docs/PlantAssist_Architecture.pptx
deploy/aws/           IAM policies for Bedrock
```

Key pieces:

- **Fan-out** (`nodes.py`): `dispatch()` returns `[Send("retrieve", RetrieveTask(**t)) for t in targets]`; LangGraph runs them in one parallel step and `merge_documents` concatenates the results.
- **Typed routing** (`router.py`): `llm.with_structured_output(RouteDecision)`; the `Literal` of allowed labels is generated from `SOURCES`.
- **Policy as code** (`router.plan_retrieval`): unit-tested rules, independent of the model.
- **Bounded loops**: max 1 query rewrite, max 2 generations - the graph always terminates.

### Chunking in one paragraph
Every file is first converted to Markdown (Word heading styles and PDF font sizes become `#` headings;
tables become pipe tables in reading order). Chunks never cross a section; tables up to
`TABLE_MAX_CHARS` (2,500) stay whole, larger ones are split by rows with the header repeated;
sections are packed up to `CHUNK_SIZE` (900 chars, ~225 tokens) and only oversized paragraphs are
split with `CHUNK_OVERLAP` (120). Each chunk starts with `Title (doc_id) > Section` and carries
`section_path` and `content_type` metadata. Result: 71 chunks, ~400 chars on average.
Details and rationale: [docs/DESIGN.md](docs/DESIGN.md#4-ingestion-pipeline-extraction-and-chunking).

### Guardrails in one paragraph
Input: prompt injection and *how-to* requests for defeating protections (light curtains, interlocks,
skipping lockout) are refused before any LLM call - reports of a violation are still answered;
emails/phone numbers are redacted. Output: invalid citations removed, **every number must appear in
the excerpts** (else regenerate, then caveat), unsafe advice is withheld, optional LLM verifier.
Response: fixed emergency banner, escalation contacts. AWS: Amazon Bedrock Guardrails via
`BEDROCK_GUARDRAIL_ID`. Guardrail evaluation: 16/16 cases correct.

## 5. Run it locally (Windows / PowerShell)

### Prerequisites
- Python 3.12
- [Ollama](https://ollama.com/download) with two models:
  ```powershell
  ollama pull llama3.2
  ollama pull nomic-embed-text
  ```

### Install
```powershell
cd 05-plant-assist
python -m venv .venv                      # skip if .venv already exists
.venv\Scripts\Activate.ps1                # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements-app.txt
pip install streamlit                     # optional UI
copy .env.example .env                    # then edit as needed
```

### Start / stop Ollama
```powershell
# start (or Start menu -> Ollama)
Start-Process "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" serve -WindowStyle Hidden
Invoke-RestMethod http://localhost:11434/api/version      # check it is up

# stop (or tray icon -> Quit Ollama)
Get-Process ollama*, llama-server -ErrorAction SilentlyContinue | Stop-Process -Force
```

### Build the index, then ask
```powershell
python -m plant_assist.cli ingest                         # first run, or after editing data/docs
python -m plant_assist.cli ask "What torque for the HP-200 gland retainer bolts?" --trace
python -m plant_assist.cli chat                           # interactive
uvicorn plant_assist.api:app --port 8005                  # REST: http://localhost:8005/docs
streamlit run ui/streamlit_app.py --server.port 8505     # web UI: http://localhost:8505
```
The API, UI and AgentCore entrypoint build the index automatically if it is missing or was
built with a different embedding model or chunking settings. Supported files per source folder:
`.md`, `.txt`, `.docx`, `.pdf` (text-based; scanned PDFs need OCR).

### Tests and evaluation
```powershell
python -m pytest -q                                       # 44 unit tests, no Ollama needed; ignores your .env
$env:RUN_INTEGRATION="1"; python -m pytest tests/test_integration.py -s   # real stack
python -m eval.run_eval --no-llm                          # retrieval hit@k / MRR, guardrails, keyword routing (~20 s)
python -m eval.run_eval                                   # + LLM router accuracy
python -m eval.run_eval --full                            # + answers: fact recall, citations, numeric grounding, latency
cd deck; npm install; node build_deck.js                  # rebuild the deck
```
Current results (`--no-llm`, nomic-embed-text): retrieval hit@5 **100%**, MRR **0.974**, guardrail
block precision/recall **1.0/1.0**, keyword-fallback routing 82%. Results are written to `eval/results.json`.

### Monitoring with LangSmith
Add to `.env`:
```ini
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_...
LANGSMITH_PROJECT=plant-assist
LANGSMITH_HIDE_INPUTS=true      # optional: keep questions / document text out of LangSmith
LANGSMITH_HIDE_OUTPUTS=true
```
Every question is then traced (nodes, router output, retrievals, prompts, tokens, latency) with tags
`provider:*` and `channel:*`; the response carries a `run_id`. Feedback from the Streamlit buttons
or `POST /feedback {"run_id": "...", "score": 1}` is attached to the run as `supervisor_rating`.
Run the labelled set as an experiment with `python -m eval.langsmith_eval`. Without LangSmith, every
question and feedback is still recorded in `logs/audit.jsonl`.

### CPU-only laptops
A 3B model on CPU uses every core while it generates. The `.env` profile used on a 4-core laptop:
```ini
OLLAMA_NUM_THREAD=2          # cap Ollama at ~50% CPU (slower answers, responsive machine)
OLLAMA_KEEP_ALIVE=60         # free the model's ~2.5 GB 60 s after the last call
OLLAMA_NUM_CTX=4096          # enough for the ~2.5k-token prompt; larger = more RAM
OLLAMA_NUM_PREDICT=512       # cap answer length
GROUNDING_CHECK=false        # llama3.2 flags almost every answer; re-enable with Claude
MAX_GENERATION_ATTEMPTS=1    # 2 LLM calls per question instead of up to 6
```
Observed on that laptop: Ollama held at ~50% CPU and ~2.9 GB RAM while answering; answers take
minutes, not seconds. For fast answers use Bedrock (below).


## Sample roles (added in the portfolio version)
| Role | Demo API key | Sources it may search |
|---|---|---|
| `floor_supervisor` | `supervisor-demo-key` | safety, maintenance, quality |
| `maintenance_technician` | `tech-demo-key` | safety, maintenance |
| `quality_engineer` | `quality-demo-key` | safety, quality |
| `ehs_manager` | `ehs-demo-key` | safety, maintenance, quality |
| `contractor` | `contractor-demo-key` | safety only |

Safety procedures are always searchable (safety-first). Sources a role may not search are removed after
routing: if nothing is left the request is `denied`; otherwise the answer carries a note that some
documentation was not available for the role. The API requires `X-API-Key`.

```powershell
curl -X POST http://localhost:8005/ask -H "X-API-Key: contractor-demo-key" -H "Content-Type: application/json" `
     -d '{"question": "How do I replace the main cylinder seal on the HP-200 press?"}'
curl http://localhost:8005/metrics       # plant_assist_requests_total{primary_source,role,outcome}, latency, guardrail blocks
```

## RAGAS
```powershell
python -m eval.ragas_eval --optimize     # non-LLM context precision / recall per retrieval mode and top_k
python -m eval.ragas_eval --llm 2        # + LLM-judged faithfulness / groundedness (use the capped judge on CPU)
```

## 6. Deploy on AWS Bedrock

### Step 1 - Enable models
In the Bedrock console for your region (e.g. `us-east-1`) -> **Model access**, enable an
**Anthropic Claude** model and **Amazon Titan Text Embeddings V2**. Find the ID to use
(newer Claude models are invoked through a cross-region inference profile):
```powershell
aws bedrock list-inference-profiles --region us-east-1 --query "inferenceProfileSummaries[?contains(inferenceProfileId,'claude')].inferenceProfileId"
```

### Step 2 - Run locally against Bedrock
```powershell
aws configure            # or: aws sso login --profile <profile>
```
In `.env`:
```ini
LLM_PROVIDER=bedrock
EMBEDDING_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=<Claude model or inference-profile ID from step 1>
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v2:0
GROUNDING_CHECK=true
MAX_GENERATION_ATTEMPTS=2
```
```powershell
python -m plant_assist.cli ask "When is a first article inspection required?" --trace
```
The index records which embedding model built it and rebuilds itself with Titan automatically.
Your IAM identity needs the permissions in [deploy/aws/bedrock-invoke-policy.json](deploy/aws/bedrock-invoke-policy.json).

### Step 3a - Deploy to Amazon Bedrock AgentCore Runtime (managed agent hosting)
`agentcore_app.py` wraps `PlantAssistant.ask()` in `BedrockAgentCoreApp` (`POST /invocations`, port 8080).
```powershell
pip install bedrock-agentcore-starter-toolkit
agentcore configure --entrypoint agentcore_app.py --requirements-file requirements-app.txt
agentcore launch          # builds an arm64 image (CodeBuild), pushes to ECR, creates the runtime
agentcore invoke '{"prompt": "What PPE is required at the parts washer?"}'
```
- Set the runtime environment variables from step 2 (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `BEDROCK_MODEL_ID`, `AWS_REGION`) - see `agentcore launch --help` for the flag in your toolkit version.
- Attach `deploy/aws/bedrock-invoke-policy.json` to the runtime's execution role.
- Local smoke test first: `python agentcore_app.py`, then `curl -X POST localhost:8080/invocations -H "Content-Type: application/json" -d '{"prompt": "When is FAI required?"}'`.

### Step 3b - Or deploy the REST API container (App Runner / ECS Fargate)
Requires Docker. The `Dockerfile` defaults to Bedrock and serves FastAPI on port 8000.
```powershell
$ACCOUNT = aws sts get-caller-identity --query Account --output text
$REGION = "us-east-1"; $REPO = "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/plant-assist"

aws ecr create-repository --repository-name plant-assist --region $REGION
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
docker build -t plant-assist .
docker tag plant-assist:latest "$REPO:latest"
docker push "$REPO:latest"

aws iam create-role --role-name PlantAssistBedrockRole --assume-role-policy-document file://deploy/aws/apprunner-trust.json
aws iam put-role-policy --role-name PlantAssistBedrockRole --policy-name bedrock-invoke --policy-document file://deploy/aws/bedrock-invoke-policy.json
```
Then in the App Runner console: **Create service** -> image `$REPO:latest`, port **8000**,
health check path **/health**, instance role **PlantAssistBedrockRole**, and the environment
variables from step 2. Test:
```powershell
Invoke-RestMethod -Method Post -Uri "https://<service-url>/ask" -ContentType "application/json" -Body '{"question": "What is the minimum Cpk for CTQ dimensions?"}'
```
For ECS Fargate use the same image, port and role as the task role.

### Production hardening (not in the prototype)
- Vector store: the container rebuilds a small Chroma index at start-up - fine for a pilot. For real document volumes move to **OpenSearch Serverless** or **Bedrock Knowledge Bases**, synced from the document management system with revision tracking.
- Auth: put the API behind Cognito / corporate SSO; restrict documents by role.
- Safety: create an **Amazon Bedrock Guardrail** (content filters, denied topics such as "bypassing safety devices", PII masking) and set `BEDROCK_GUARDRAIL_ID` / `BEDROCK_GUARDRAIL_VERSION`; the deterministic guardrails and emergency banner stay on.
- Observability: CloudWatch logs; LangSmith tracing and feedback; ship `logs/audit.jsonl` to S3/CloudWatch; every response includes the graph `trace` and `run_id`.

## 7. Configuration reference

All settings come from environment variables or `.env` (see [.env.example](.env.example)).

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` / `EMBEDDING_PROVIDER` | `ollama` | `ollama` or `bedrock` |
| `OLLAMA_CHAT_MODEL` / `OLLAMA_EMBEDDING_MODEL` | `llama3.2` / `nomic-embed-text` | local models |
| `OLLAMA_NUM_THREAD` | all cores | CPU cap for inference |
| `OLLAMA_KEEP_ALIVE` | `60` | seconds the model stays in RAM after a call |
| `OLLAMA_NUM_CTX` / `OLLAMA_NUM_PREDICT` | `4096` / `512` | context window / max answer tokens |
| `BEDROCK_MODEL_ID` | - | Claude model or inference-profile ID (required for bedrock) |
| `BEDROCK_EMBEDDING_MODEL_ID` | `amazon.titan-embed-text-v2:0` | embeddings on Bedrock |
| `TOP_K` / `POLICY_TOP_K` | `5` / `2` | chunks per routed / policy-added source |
| `MAX_CONTEXT_CHUNKS` | `6` | excerpts passed to the generator |
| `MIN_RELEVANCE` | `0.55` | cosine floor for a chunk to count as relevant |
| `ROUTE_CONFIDENCE_THRESHOLD` | `0.6` | below this, search every source |
| `MAX_QUERY_REWRITES` | `1` | corrective retrieval loop |
| `GROUNDING_CHECK` / `MAX_GENERATION_ATTEMPTS` | `true` / `2` | LLM verifier and regeneration loop |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` / `TABLE_MAX_CHARS` | `900` / `120` / `2500` | chunking, in characters (changes trigger a re-index) |
| `MAX_QUESTION_CHARS` | `1000` | input size guardrail |
| `NUMERIC_GROUNDING_CHECK` | `true` | every number in an answer must appear in the excerpts |
| `BEDROCK_GUARDRAIL_ID` / `BEDROCK_GUARDRAIL_VERSION` | - / `DRAFT` | Amazon Bedrock Guardrail on every Claude call |
| `AUDIT_LOG_PATH` | `logs/audit.jsonl` | local audit trail; empty = off |
| `LANGSMITH_TRACING` / `LANGSMITH_API_KEY` / `LANGSMITH_PROJECT` | off | LangSmith tracing, feedback, experiments |

## 8. Adding a knowledge source
1. Add an entry to `SOURCES` in [plant_assist/sources.py](plant_assist/sources.py) (description, keywords, answer guidance, escalation contact).
2. Put files in `data/docs/<folder>/`: Markdown with `doc_id` / `title` / `revision` front matter, or Word/PDF with a `Document ID: ...` / `Revision: ...` header block.
3. `python -m plant_assist.cli ingest`.

The router prompt, routing schema and keyword fallback pick it up automatically.

## 9. Known limitations
- Small local models are slow on CPU and their grounding checker is too strict; use Claude on Bedrock for real use.
- Single-turn only (no follow-up memory yet - add a LangGraph checkpointer).
- BM25 stemming is a crude suffix stripper; fine for this corpus.
- Scanned PDFs (no text layer), merged table cells and diagrams are not handled - use OCR (Textract) / a vision model.
- Guardrail patterns are English keyword rules - pair them with Bedrock Guardrails in production.
- The evaluation sets are small (28 + 16 questions) and synthetic.
