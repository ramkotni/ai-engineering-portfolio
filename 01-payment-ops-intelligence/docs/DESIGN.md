# Payment Operations Intelligence - Design Document

Portfolio prototype on synthetic data. Companion: [README](../README.md), [slides](Payment_Ops_Intelligence.pptx).

## 1. Problem and goals
Payment operations teams investigate failed payments (rejected ACH files, duplicate wires, timeouts, routing
errors, reconciliation breaks, credential expiry, late settlement). Evidence is spread across incident exports
(CSV), weekly monitoring reports (HTML) and a runbook. Goals:

| Goal | Design response |
|---|---|
| Explain *why* a failure happened | RCA Agent over semantically similar historical incidents, citing incident IDs |
| Recommend *what to do* | Recommendation Agent combining past resolutions with business rules |
| Show *whether it is getting worse* | Trend Agent: deterministic pandas analytics, LLM only narrates |
| Brief leadership | Summary Agent, tone tailored to the caller's role |
| Never move money | Read-only guardrail: commands to release / approve / cancel / re-send are refused |
| Trustworthy numbers | Numeric + incident-ID grounding on every answer |

**Users:** payment operations analysts and managers, finance executives, internal auditors and contracted IT
support engineers - see the roles in section 5 and the user table in the [README](../README.md#who-uses-it).

## 2. Architecture
```
CLI / FastAPI :8001 / Streamlit :8501
        -> PaymentOpsAssistant.ask(question, role)
        -> LangGraph supervisor graph
             guard_input -> intent_agent -> authorize (RBAC) -> supervisor <-> agents -> compose -> guard_output
        -> ChromaDB (incidents | knowledge)  +  pandas analytics  +  Ollama (llama3.2, nomic-embed-text)
        -> LangSmith traces, /metrics, logs/audit.jsonl
```

### Why multi-agent here
Unlike a single-domain Q&A bot, the requests need **different tools and reasoning**: semantic retrieval (Search),
causal reasoning over evidence (RCA), rule application (Recommendation), numeric analytics (Trend) and audience-aware
writing (Summary). A supervisor graph runs only the agents a request needs, in a fixed, auditable order:

| Intent | Plan |
|---|---|
| search | Search |
| rca | Search -> RCA (-> Recommendation if the user also asks what to do and the role allows it) |
| recommendation | Search -> Recommendation |
| trend | Trend |
| summary | Trend -> Summary |

The plan is deterministic per intent (not chosen by an LLM loop) so cost and behaviour are predictable;
each agent writes `state.outputs[name]` and later agents read earlier outputs (RCA -> Recommendation).

## 3. Agents
| Agent | Input | Output | LLM | Fallback |
|---|---|---|---|---|
| Intent | question | intent, category, system, payment type, months, confidence | structured output (JSON schema) | keyword classifier |
| Search | question + category filter | top-k incidents + report/rule chunks | none | - |
| RCA | similar incidents | ranked probable causes with incident IDs | 1 call | extract root causes of top-3 incidents |
| Recommendation | resolutions + rules (+ RCA) | numbered actions citing incident / rule IDs | 1 call | list past resolutions |
| Trend | filters | analytics table + narrative | narrates only | analytics table |
| Summary | trend + recent Sev1/2 + report commentary | executive or operational summary | 1 call | facts list |

**Slot grounding**: the Intent Agent's filters (system, payment type, months) are kept only if the question
mentions them - small models invent filters (observed: "Vendor Master", "ACH", "2022-08" for a question that
named none of them).

## 4. Data and RAG pipeline
| Source | Extraction | Chunking | Why |
|---|---|---|---|
| `incidents.csv` (60 rows) | csv | **one document per row**; every column also stored as metadata | an incident is the unit of evidence; splitting would separate symptom, root cause and resolution |
| `reports/*.html` (3) | BeautifulSoup -> Markdown (headings, lists, tables) | structure-aware: never cross a section, tables kept whole, 800-char target, 100 overlap for long paragraphs | sections answer different questions (commentary vs tables) |
| `business_rules.md` | as is | same chunker | each rule section is self-contained |

Every chunk gets a contextual header (`Title (ID) > Section`). Embeddings: `nomic-embed-text` with
`search_document:` / `search_query:` prefixes. Store: ChromaDB, two collections (`incidents` 60, `knowledge` 19),
cosine. Retrieval: hybrid vector + BM25 fused with reciprocal rank fusion, plus metadata filters (failure
category from the Intent Agent; doc_type for rules). The index stores a fingerprint (embedding model + chunk
settings) and rebuilds itself when they change.

## 5. Roles (RBAC)
Defined in `payops/roles.yaml`; API key -> role.
| Role | Intents | Amounts |
|---|---|---|
| payment_analyst | all five | visible |
| operations_manager | all five | visible |
| executive | trend, summary (executive style) | visible |
| auditor | search, trend, summary | visible |
| support_engineer | search, rca | masked |

Enforced in the `authorize` node (intent permission, plan pruning) and in `guard_output` (amount masking).

## 6. Guardrails
| Layer | Guardrail | Behaviour |
|---|---|---|
| Input | Prompt injection | blocked before any LLM call |
| Input | Action commands (release / approve / cancel / re-send payments, change bank details) | refused - read-only assistant; process questions allowed |
| Input/Output | Bank numbers, emails, phones | redacted |
| Output | Numeric grounding | numbers must appear in evidence, analytics or the question; otherwise a visible caveat |
| Output | Incident-ID grounding | cited PAY-INC IDs must exist in retrieved evidence |
| Output | RBAC amount masking | `[amount restricted]` for roles without financial visibility |

## 7. Evaluation
Datasets in `eval/datasets/`: 22 intent questions, 10 RAG questions with references, 12 guardrail cases.

| Metric | Result |
|---|---|
| Intent accuracy (keyword fallback, 22 questions) | 100% (category 95.5%) |
| Retrieval hit@6 / MRR / precision@6 (category match) | 1.0 / 1.0 / 0.833 |
| Guardrail block precision / recall (12 cases) | 1.0 / 1.0 |
| Analytics vs independent pandas | 7 / 7 checks; planted duplicate-payment rise detected |
| RAGAS non-LLM context precision / recall (hybrid, k=6) | 0.789 / 0.771 |
| RAGAS LLM context recall (llama3.2 judge, 2 answers) | 1.0, 1.0 |
| RAGAS faithfulness (llama3.2 judge) | not obtained - the 3B judge failed the metric's structured output (InstructorRetryException); use a stronger judge (`RAGAS_JUDGE_PROVIDER=openai`) or Bedrock/Claude |
| End-to-end latency (RCA, 2 CPU threads) | ~150 s |

### RAGAS-driven optimisation
`python -m eval.ragas_eval --optimize` sweeps retrieval mode x top_k on non-LLM context precision / recall:

| Mode | k=3 | k=6 | k=10 (F1) |
|---|---|---|---|
| vector | 0.777 | 0.780 | 0.781 |
| BM25 | 0.592 | 0.651 | 0.665 |
| hybrid | 0.763 | **0.780** (current) | 0.776 |

Finding: BM25 alone is clearly worse; vector and hybrid tie within noise, so the current hybrid k=6 is kept
(BM25 still helps exact IDs and codes). The optimiser only recommends a change when it beats the current
setting by more than 0.01 F1.

## 8. Monitoring
- **LangSmith**: every node, LLM call and retrieval traced; tags `role:*`, `channel:*`, `provider:*`; feedback
  (`POST /feedback`, UI buttons) attached as `user_rating`; `eval/langsmith_eval.py` runs experiments.
- **Prometheus metrics** (`/metrics`): `payops_requests_total{intent,role,outcome}`, latency histogram,
  `payops_guardrail_blocks_total{category}`, `payops_output_guardrail_flags_total`, `payops_intent_fallback_total`,
  `payops_feedback_total`. JSON at `/metrics/summary`.
- **Audit log**: `logs/audit.jsonl`.
- Suggested alerts: p95 latency, denied / blocked rate, output-guardrail flag rate, intent fallback rate, negative feedback.

## 9. Tech stack
LangGraph 1.2, LangChain core 1.6, Ollama (llama3.2, nomic-embed-text), ChromaDB 1.5, BM25 (in-process),
pandas, BeautifulSoup, FastAPI, Streamlit, LangSmith, RAGAS 0.4.3, pytest (29 tests).

## 10. Limitations and next steps
Single-turn; synthetic data; small local judge for RAGAS; read-only by design. Next: scheduled ingestion of
live exports, ticket creation (human-approved), checkpointer for multi-step investigations, RAGAS with a
stronger judge as a CI gate.
