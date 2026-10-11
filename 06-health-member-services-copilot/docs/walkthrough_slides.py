"""Appendix: code walkthrough slides. Executed by build_presentation.py (shares its helpers)."""
# ruff: noqa: F821  (helpers are injected from build_presentation.py)

# ------------------------------------------------------------ divider ----
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
bg.fill.solid()
bg.fill.fore_color.rgb = DARK
bg.line.fill.background()
text_box(s, Inches(0.9), Inches(2.4), Inches(11.5), Inches(1.0), "Part 2: Code walkthrough", size=44, bold=True, color=WHITE)
text_box(s, Inches(0.9), Inches(3.5), Inches(11.5), Inches(1.6), [
    "Repository map · libraries · code-level architecture · end-to-end request flow",
    "Every module, class and function · RAG & evaluation pipelines · commands (local & Bedrock)",
], size=18, color=LIGHT)
s.notes_slide.notes_text_frame.text = (
    "Use this section when the interviewer asks 'show me the code' or 'how does a request flow through the system'. "
    "Each slide maps to a file; the worked example (CLM-10002) ties it all together."
)

# ------------------------------------------------------- repo map --------
s = new_slide("Repository map", "agentic-rag-copilot/: one responsibility per module",
              notes="Walk top-down: config feeds everything; service is the only entry into the graph; the graph only "
                    "depends on interfaces (LLM, KnowledgeBase, ClaimsRepository, Guardrails), which is what makes it testable and portable.")
code_box(s, Inches(0.6), Inches(1.6), Inches(5.6), Inches(5.2), """
agentic-rag-copilot/
├─ app/
│  ├─ config.py          # Settings (env vars)
│  ├─ providers.py       # LLM + embeddings factory
│  ├─ ingest.py          # RAG indexing pipeline (CLI)
│  ├─ vectorstore.py     # KnowledgeBase: Chroma | Bedrock KB
│  ├─ tools.py           # Claims tool + authZ
│  ├─ guardrails.py      # PII, injection, Bedrock GR
│  ├─ prompts.py         # all prompt templates
│  ├─ service.py         # AgentService.ask() entry point
│  ├─ api.py             # FastAPI + AgentCore contract
│  ├─ agentcore_entrypoint.py
│  ├─ logging_config.py  # JSON logs
│  ├─ observability.py   # LangSmith tracing + feedback
│  ├─ static/index.html  # demo chat UI
│  └─ graph/
│     ├─ state.py        # AgentState + schemas
│     ├─ nodes.py        # agents (node functions)
│     └─ builder.py      # StateGraph wiring
├─ data/policies/*.md    # 8 sample policy docs
├─ data/claims/claims.json
├─ eval/                 # golden set + harness
├─ tests/                # 74 tests (fakes, red-team)
├─ deploy/aws/           # guardrail, IAM, AgentCore
└─ docs/                 # this deck (generated)
""", size=10)
table(s, Inches(6.6), Inches(1.6), Inches(6.1), [
    ["Layer", "Files"],
    ["Entry points", "api.py · agentcore_entrypoint.py · ingest.py · eval/run_eval.py"],
    ["Application service", "service.py"],
    ["Orchestration", "graph/builder.py · graph/nodes.py · graph/state.py"],
    ["Capabilities (ports)", "providers.py · vectorstore.py · tools.py · guardrails.py"],
    ["Configuration", "config.py · .env · prompts.py"],
    ["Infra / ops", "Dockerfile · docker-compose.yml · deploy/aws · .github/workflows"],
], col_widths=[1.9, 4.2], size=12, row_h=0.6)

# ------------------------------------------------------- libraries -------
s = new_slide("Libraries used, and why", "Pinned in requirements.lock (LangChain 1.4, LangGraph 1.2, langchain-aws 1.8)",
              notes="Be ready to justify each dependency. The theme: standard, well-supported building blocks; nothing custom "
                    "where a maintained library exists, and every provider-specific library sits behind a factory.")
table(s, Inches(0.6), Inches(1.55), Inches(12.1), [
    ["Library", "Used in", "What we use it for"],
    ["langgraph", "graph/builder.py, state.py", "StateGraph, START/END, conditional edges, add_messages reducer, checkpointers (InMemorySaver)"],
    ["langgraph-checkpoint-sqlite", "graph/builder.py", "SqliteSaver: durable conversation memory (CHECKPOINTER=sqlite)"],
    ["langchain-core", "nodes.py, providers.py", "BaseChatModel, messages, Document, Embeddings, with_structured_output()"],
    ["langchain-text-splitters", "ingest.py", "MarkdownHeaderTextSplitter + RecursiveCharacterTextSplitter"],
    ["langchain-ollama", "providers.py", "ChatOllama (llama3.2), OllamaEmbeddings (nomic-embed-text)"],
    ["langchain-chroma / chromadb", "vectorstore.py, ingest.py", "Chroma vector store (cosine), similarity_search_with_relevance_scores"],
    ["langchain-aws", "providers.py, vectorstore.py", "ChatBedrockConverse (Claude), BedrockEmbeddings (Titan V2), AmazonKnowledgeBasesRetriever"],
    ["boto3", "guardrails.py, deploy/aws", "ApplyGuardrail, create_guardrail, AgentCore control plane, invoke_agent_runtime"],
    ["bedrock-agentcore", "agentcore_entrypoint.py", "BedrockAgentCoreApp + @app.entrypoint (starter-toolkit deploy path)"],
    ["fastapi / uvicorn", "api.py", "HTTP API, dependency injection, lifespan startup, /invocations + /ping"],
    ["pydantic / pydantic-settings", "config.py, state.py, service.py", "Typed settings from env, structured-output schemas, request/response models"],
    ["langsmith", "observability.py, eval/langsmith_eval.py", "Tracing config, feedback, datasets + evaluate() experiments"],
    ["pytest · httpx · ruff · python-pptx", "tests/, docs/", "Unit tests + TestClient, linting, generating this deck"],
], col_widths=[2.6, 2.8, 6.7], size=11, row_h=0.4)

# ------------------------------------------- code-level architecture -----
s = new_slide("Code-level architecture", "Who calls whom: entry points → service → graph → capabilities",
              notes="Arrows show call direction. Only service.py touches the graph; only nodes.py touches capabilities. "
                    "Ingestion bypasses the graph and writes straight to the vector store.")
entry = [("app/api.py", "FastAPI /chat · /invocations"), ("app/agentcore_entrypoint.py", "BedrockAgentCoreApp"),
         ("eval/run_eval.py", "evaluation harness"), ("app/ingest.py", "CLI: build the index")]
for i, (f, d) in enumerate(entry):
    box(s, Inches(0.6 + i * 3.1), Inches(1.55), Inches(2.8), Inches(0.8), f"{f}\n{d}", fill=WHITE, line=BLUE, size=12, bold=True)
box(s, Inches(0.6), Inches(2.85), Inches(8.9), Inches(0.8),
    "app/service.py: AgentService.ask(ChatRequest) → ChatResponse\nedge PII redaction · per-turn state reset · thread_id · structured logging",
    fill=LIGHT, size=13, bold=True)
for i in range(3):
    cx = Inches(0.6 + i * 3.1 + 1.4)
    arrow(s, cx, Inches(2.35), cx, Inches(2.85))
graph_boxes = [("app/graph/builder.py", "build_graph() · routing fns\nmake_checkpointer()"),
               ("app/graph/nodes.py", "AgentNodes (13 nodes)\ninvoke_structured · critic"),
               ("app/graph/state.py", "AgentState · RouteDecision\nGradeResult · Groundedness")]
for i, (f, d) in enumerate(graph_boxes):
    box(s, Inches(0.6 + i * 3.1), Inches(4.05), Inches(2.8), Inches(0.95), f"{f}\n{d}", fill=LIGHT, size=12, bold=True)
arrow(s, Inches(2.0), Inches(3.65), Inches(2.0), Inches(4.05))
arrow(s, Inches(3.4), Inches(4.52), Inches(3.7), Inches(4.52))
arrow(s, Inches(6.5), Inches(4.52), Inches(6.8), Inches(4.52))
caps = [("providers.py", "ChatOllama | Bedrock"), ("prompts.py", "templates"), ("tools.py", "ClaimsRepository"),
        ("guardrails.py", "Guardrails"), ("vectorstore.py", "Chroma | Bedrock KB")]
for i, (f, d) in enumerate(caps):
    x = Inches(0.6 + i * 2.45)
    box(s, x, Inches(5.4), Inches(2.25), Inches(0.75), f"{f}\n{d}", fill=WHITE, size=12, bold=True)
    arrow(s, Inches(5.1), Inches(5.0), x + Inches(1.12), Inches(5.4), dashed=True)
arrow(s, Inches(11.3), Inches(2.35), Inches(11.3), Inches(5.4), color=BLUE, label="ingest → upsert")
text_box(s, Inches(0.6), Inches(6.35), Inches(12), Inches(0.4),
         "app/config.py: Settings (pydantic-settings, cached by get_settings()) is passed into every component · logging_config.py: JSON logs",
         size=12, color=MUTED)

# ------------------------------------------- end-to-end request flow -----
s = new_slide("End-to-end request flow", "What happens when a member clicks Send in the UI",
              notes="Narrate this as a story; it's the single most useful slide for 'walk me through the code'.")
table(s, Inches(0.6), Inches(1.5), Inches(12.1), [
    ["#", "Where (file → function)", "What happens"],
    ["1", "static/index.html → fetch('/chat')", "POST {question, session_id, member_id}"],
    ["2", "api.py → chat()", "Pydantic validates ChatRequest; require_api_key; run_in_threadpool(service.ask)"],
    ["3", "service.py → AgentService.ask()", "Guardrails.sanitize() redacts PII before logs / memory / LLM"],
    ["4", "state.py → initial_turn_state()", "Reset per-turn fields; config thread_id = session_id (memory key)"],
    ["5", "graph.invoke()  (builder.py)", "LangGraph runs nodes from START; checkpointer loads prior messages"],
    ["6", "nodes.py → input_guard → supervisor", "Block injection / route intent + rewrite follow-up into standalone question"],
    ["7", "claims_agent / retrieve → grade → generate", "Tool lookup (authZ) and/or RAG over Chroma; LLM writes cited answer"],
    ["8", "groundedness_check → output_guard", "Critic verifies $ / % / deadlines; redact PII; optional Bedrock check"],
    ["9", "finalize", "AIMessage appended → persisted by checkpointer for the next turn"],
    ["10", "service.py → ChatResponse + log_event()", "answer, intent, citations, grounded, guardrail flags, trace, latency"],
], col_widths=[0.5, 4.1, 7.5], size=12, row_h=0.45)

# ----------------------------------------- config + providers ------------
s = new_slide("config.py · providers.py", "Configuration and the model provider factory",
              notes="The factory is the seam that lets the same graph run on Ollama or Bedrock. The judge model can be "
                    "different (stronger) than the model under test.")
table(s, Inches(0.6), Inches(1.5), Inches(7.2), [
    ["Symbol", "What it does"],
    ["class Settings(BaseSettings)", "All config from env/.env: providers, model IDs, retrieval k/threshold, agent toggles, guardrails, memory, API key"],
    ["Settings.effective_embeddings_provider", "Embeddings provider, defaulting to the LLM provider"],
    ["Settings.collection_name", "policy_docs_<provider>: separate collection per embedding dimension"],
    ["get_settings()", "@lru_cache singleton"],
    ["get_chat_model(settings, provider, model, temperature)", "ChatOllama(num_ctx, timeout) or ChatBedrockConverse(adaptive retries)"],
    ["get_judge_model(settings)", "LLM-as-judge for eval (EVAL_JUDGE_PROVIDER / MODEL)"],
    ["get_embeddings(settings)", "OllamaEmbeddings(nomic) or BedrockEmbeddings(Titan V2)"],
], col_widths=[3.2, 4.0], size=11, row_h=0.55)
code_box(s, Inches(8.1), Inches(1.9), Inches(4.6), Inches(4.3), """
# providers.py (simplified)
def get_chat_model(settings, provider=None):
    if provider == "ollama":
        return ChatOllama(
            model=s.ollama_chat_model,
            base_url=s.ollama_base_url,
            temperature=0, num_ctx=8192)
    if provider == "bedrock":
        return ChatBedrockConverse(
            model=s.bedrock_chat_model_id,
            region_name=s.aws_region,
            config=Config(retries={
              "mode": "adaptive"}))
""", size=10, title="Swap providers with one env var")

# ------------------------------------------------- RAG indexing ----------
s = new_slide("RAG pipeline, part 1: indexing (ingest.py)", "python -m app.ingest --reset   (or AUTO_INGEST on first start)",
              notes="Indexing is offline and idempotent. Re-running never duplicates chunks because IDs are content hashes.")
flow = [("load_markdown()", "data/policies/*.md\n→ Document(source)"),
        ("chunk_documents()", "split by # / ## headers,\nthen 900-char chunks"),
        ("contextual header", "prefix 'Title > Section'\nto every chunk"),
        ("chunk_id()", "sha256(source|section|\npart|content)[:24]"),
        ("ChromaKnowledgeBase", "store.add_documents(\nchunks, ids=ids)")]
for i, (t, d) in enumerate(flow):
    x = Inches(0.5 + i * 2.5)
    box(s, x, Inches(1.6), Inches(2.2), Inches(1.15), f"{t}\n{d}", size=12, bold=True)
    if i:
        arrow(s, x - Inches(0.3), Inches(2.17), x, Inches(2.17))
table(s, Inches(0.6), Inches(3.2), Inches(6.4), [
    ["Function", "Purpose"],
    ["load_markdown(docs_dir)", "Read every .md file into a LangChain Document"],
    ["chunk_documents(docs, settings)", "Header-aware + size split; metadata: source, title, section, part"],
    ["chunk_id(doc)", "Deterministic ID makes upserts idempotent"],
    ["ingest(settings, reset, embeddings)", "reset_collection() if --reset, embed, upsert; returns chunk count"],
    ["main()", "CLI entry: argparse --reset, logging, print summary"],
], col_widths=[2.6, 3.8], size=11, row_h=0.5)
code_box(s, Inches(7.4), Inches(3.55), Inches(5.3), Inches(2.9), """
# Trigger indexing
python -m app.ingest --reset
# -> Ingested 42 chunks into 'policy_docs_ollama'

# Add your own documents
copy my_policy.md data\\policies\\
python -m app.ingest      # upsert, no duplicates

# Index with Bedrock Titan embeddings
# (.env: LLM_PROVIDER=bedrock)
python -m app.ingest --reset
""", size=10, title="Commands")

# ------------------------------------------------- vectorstore -----------
s = new_slide("vectorstore.py: the KnowledgeBase interface", "The graph depends on a Protocol, not on Chroma",
              notes="Program to an interface: tests use FakeKB, local uses Chroma, prod can use Bedrock Knowledge Bases, "
                    "and the graph code never changes.")
table(s, Inches(0.6), Inches(1.5), Inches(7.4), [
    ["Symbol", "What it does"],
    ["@dataclass RetrievedChunk", "content, source, section, score, metadata; to_dict() for state"],
    ["class KnowledgeBase(Protocol)", "search(query, k) -> list[RetrievedChunk]; count() -> int"],
    ["class ChromaKnowledgeBase", "Chroma(collection, embeddings, persist_dir, cosine)"],
    ["  .search(query, k)", "similarity_search_with_relevance_scores, then drop score < RELEVANCE_THRESHOLD (0.50)"],
    ["  .count()", "chunks in the collection (used for auto-ingest + /health)"],
    ["class BedrockKnowledgeBase", "AmazonKnowledgeBasesRetriever(knowledge_base_id); maps S3 URI → source"],
    ["get_knowledge_base(settings)", "Factory on VECTOR_BACKEND = chroma | bedrock_kb"],
], col_widths=[2.9, 4.5], size=11, row_h=0.55)
code_box(s, Inches(8.3), Inches(1.9), Inches(4.4), Inches(3.4), """
class KnowledgeBase(Protocol):
    def search(self, query: str,
               k: int) -> list[RetrievedChunk]: ...
    def count(self) -> int: ...

# Measured on nomic-embed-text:
#  relevant chunks   0.68 - 0.80
#  off-topic query  <= 0.42
#  -> threshold 0.50
""", size=10, title="Interface + calibration")

# ------------------------------------------------- state ----------------
s = new_slide("graph/state.py: shared state and schemas", "One TypedDict flows through every node; nodes return partial updates",
              notes="Explain the reducer: messages uses add_messages so each turn appends; every other key is overwritten. "
                    "initial_turn_state resets per-turn keys so stale documents from the previous turn can't leak in.")
table(s, Inches(0.6), Inches(1.5), Inches(6.6), [
    ["AgentState key", "Written by", "Meaning"],
    ["messages (add_messages)", "input_guard, finalize", "Conversation memory (persisted)"],
    ["question / member_id", "service", "Sanitized question, signed-in member"],
    ["intent, standalone_question", "supervisor", "Route + rewritten follow-up"],
    ["claim_id, claim", "supervisor, claims_agent", "Claim lookup result"],
    ["search_query, documents", "retrieve, rewrite, claims", "Query and retrieved chunks"],
    ["answer, citations", "generate, guards", "Draft → final answer"],
    ["grounded, regenerations", "groundedness_check", "Critic verdict + loop counter"],
    ["guardrail, trace, rewrites", "many", "Flags, node path, loop counter"],
], col_widths=[2.3, 2.1, 2.2], size=11, row_h=0.47)
table(s, Inches(7.5), Inches(1.5), Inches(5.2), [
    ["Pydantic schema", "Used by"],
    ["RouteDecision(intent, standalone_question, claim_id)", "supervisor"],
    ["GradeResult(relevant_ids)", "grade_documents"],
    ["RewriteResult(query)", "rewrite_query"],
    ["GroundednessResult(grounded, unsupported_claims)", "groundedness_check (llm mode)"],
], col_widths=[3.5, 1.7], size=11, row_h=0.5)
text_box(s, Inches(7.5), Inches(4.4), Inches(5.2), Inches(1.5), [
    "initial_turn_state(question, member_id, flags)",
    "Resets every per-turn key at the start of each turn; messages is untouched so memory survives.",
], size=12, color=MUTED)

# ------------------------------------------------- nodes helpers ---------
s = new_slide("graph/nodes.py, part 1: helpers", "Reliability utilities used by the agents",
              notes="invoke_structured is the reason the graph never crashes on a malformed LLM reply: native structured output, "
                    "then JSON extraction, then a safe default. unsupported_numbers is the deterministic critic.")
table(s, Inches(0.6), Inches(1.5), Inches(7.0), [
    ["Symbol", "What it does"],
    ["@dataclass Deps", "Dependency bundle: llm, kb, claims, guardrails, settings (injected; fakes in tests)"],
    ["invoke_structured(llm, schema, msgs, default)", "1) with_structured_output  2) parse JSON from text  3) safe default"],
    ["unsupported_numbers(answer, context)", "Type-aware critic: $ amounts, %, and day/month/hour limits must exist in context"],
    ["claim_summary(claim)", "Deterministic claim facts: status, amount owed, denial reason"],
    ["_INSURANCE_TERMS (regex)", "Overrides an 'out_of_scope' route when the question is clearly about insurance"],
    ["_build_context(state)", "[CLAIM] record + numbered [1..n] chunks for the prompt and the critic"],
    ["_format_history(state, window)", "Last N messages as text for the supervisor"],
], col_widths=[3.0, 4.0], size=11, row_h=0.55)
code_box(s, Inches(7.9), Inches(1.9), Inches(4.8), Inches(4.4), """
def invoke_structured(llm, schema, msgs, default):
    try:   # Ollama JSON-schema / Bedrock tools
        return llm.with_structured_output(
                   schema).invoke(msgs)
    except Exception:
        pass
    try:   # fallback: parse JSON from text
        raw = llm.invoke(msgs).content
        return schema.model_validate(
                   _extract_json(raw))
    except Exception:
        return default   # never crash
""", size=10, title="Graceful degradation")

# ------------------------------------------------- nodes (agents) --------
s = new_slide("graph/nodes.py, part 2: AgentNodes (the agents)", "Each method = one LangGraph node: reads state, returns a partial update",
              notes="Point out which nodes call the LLM (supervisor, grade, rewrite, generate, critic in llm mode) and which are "
                    "pure code (guards, claims, retrieve, fallback, finalize). Pure-code nodes are fast, free and deterministic.")
table(s, Inches(0.6), Inches(1.45), Inches(12.1), [
    ["Node method", "LLM?", "Reads", "Writes / does"],
    ["input_guard", "no", "question", "check_input(): injection, length, Bedrock GR → guardrail.blocked; add HumanMessage"],
    ["blocked", "no", "-", "answer = BLOCKED_MESSAGE"],
    ["supervisor", "yes", "question, history", "RouteDecision → intent, claim_id (regex override), standalone_question"],
    ["direct_response", "no", "intent", "Canned greeting / out-of-scope reply"],
    ["claims_agent", "no", "claim_id, member_id", "ClaimsRepository.get_claim (authZ); list claims; denial → search_query for policy"],
    ["retrieve", "no", "search_query", "kb.search(k=4) → documents"],
    ["grade_documents", "yes", "documents", "GradeResult → keep relevant chunks only"],
    ["rewrite_query", "yes", "standalone_question", "RewriteResult → better search_query; rewrites += 1"],
    ["fallback", "no", "-", "answer = escalate to Member Services"],
    ["generate", "yes", "context, history", "Cited answer (+ claim_summary prefix), citations"],
    ["groundedness_check", "mode", "answer, context", "numeric and/or LLM critic → grounded; regenerations += 1"],
    ["output_guard", "no", "answer, grounded", "Ungrounded → fallback; redact PII not in sources; Bedrock check"],
    ["finalize", "no", "answer", "Append AIMessage → saved by the checkpointer"],
], col_widths=[2.2, 0.8, 2.3, 6.8], size=11, row_h=0.38)

# ------------------------------------------------- builder ---------------
s = new_slide("graph/builder.py: wiring the graph", "Nodes + conditional edges + checkpointer = compiled, runnable agent",
              notes="Routing functions are plain Python. That's where bounded loops live (max rewrites / regenerations), which "
                    "is why the graph can't spin forever. recursion_limit=25 is the last-resort backstop in service.py.")
code_box(s, Inches(0.6), Inches(1.95), Inches(6.7), Inches(4.8), """
def build_graph(deps, checkpointer=None):
    n = AgentNodes(deps)
    g = StateGraph(AgentState)
    g.add_node("supervisor", n.supervisor)  # ...13 nodes
    g.add_edge(START, "input_guard")
    g.add_conditional_edges("supervisor",
        lambda st: st["intent"], {
          "policy_question": "retrieve",
          "claim_status":    "claims_agent",
          "greeting":        "direct_response",
          "out_of_scope":    "direct_response"})
    g.add_conditional_edges("grade_documents",
        after_grading, {...})
    g.add_edge("rewrite_query", "retrieve")  # loop
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)
""", size=10, title="build_graph()")
table(s, Inches(7.6), Inches(1.55), Inches(5.1), [
    ["Routing function", "Decision"],
    ["after input_guard (lambda)", "blocked → blocked, else supervisor"],
    ["after_claims(st)", "answered → output_guard; denial → retrieve; else generate"],
    ["after_grading(st)", "docs → generate; rewrites < max → rewrite; claim → generate; else fallback"],
    ["after_groundedness(st)", "ungrounded and regenerations ≤ max → generate; else output_guard"],
    ["make_checkpointer(settings)", "InMemorySaver or SqliteSaver(sqlite3)"],
], col_widths=[2.1, 3.0], size=11, row_h=0.62)

# ------------------------------------------------- guardrails + tools ----
s = new_slide("guardrails.py · tools.py", "Safety and authorization live in code, not in prompts",
              notes="Two talking points: (1) the claims tool returns the same message for 'not found' and 'not yours', which "
                    "prevents claim-ID enumeration; (2) the Bedrock guardrail is fail-closed by default.")
table(s, Inches(0.6), Inches(1.5), Inches(7.3), [
    ["Symbol (guardrails.py)", "What it does"],
    ["find_pii(text) / redact_pii(text, allow)", "Regex SSN, card (Luhn-checked), email, phone → [REDACTED_X]"],
    ["detect_prompt_injection(text)", "Pattern list: 'ignore previous instructions', 'developer mode', ..."],
    ["@dataclass GuardrailResult", "blocked, reason, flags, text"],
    ["class BedrockGuardrail.check(...)", "ApplyGuardrail API (INPUT/OUTPUT, grounding qualifiers); fail-closed"],
    ["Guardrails.sanitize(text)", "Edge: PII redaction before the graph"],
    ["Guardrails.check_input(text)", "Empty/length/injection rules, then Bedrock"],
    ["Guardrails.check_output(answer, context)", "Redact PII not in sources (allowlist official numbers) + Bedrock grounding"],
], col_widths=[3.2, 4.1], size=11, row_h=0.52)
table(s, Inches(8.2), Inches(1.5), Inches(4.5), [
    ["Symbol (tools.py)", "What it does"],
    ["extract_claim_id(text)", "Regex CLM-12345 (lenient)"],
    ["@dataclass ClaimLookup", "found, authorized, claim, message"],
    ["ClaimsRepository.get_claim(id, member)", "Ownership check; same reply for 'missing' and 'not yours'"],
    ["ClaimsRepository.list_claims(member)", "Member's own claims only"],
], col_widths=[2.3, 2.2], size=11, row_h=0.6)

# ------------------------------------------------- service + api ---------
s = new_slide("service.py · api.py · agentcore_entrypoint.py", "One service, three ways in",
              notes="AgentService is the single entry point, so the API, the AgentCore entrypoint and the evaluation harness all "
                    "exercise exactly the same code path. That's why evaluation results are representative of production.")
table(s, Inches(0.6), Inches(1.5), Inches(6.3), [
    ["Symbol", "What it does"],
    ["ChatRequest / ChatResponse", "Pydantic API contract (question ≤ 8000 chars)"],
    ["AgentService.from_settings()", "Build KB (auto-ingest if empty), LLM, claims, guardrails → graph"],
    ["AgentService.ask(req)", "sanitize → initial_turn_state → graph.invoke(thread_id) → response + log"],
    ["api.lifespan()", "Logging + service created once at startup"],
    ["require_api_key()", "Constant-time x-api-key check when API_KEY is set"],
    ["agentcore_entrypoint.invoke()", "@app.entrypoint for the AgentCore SDK / starter toolkit"],
    ["logging_config.JsonFormatter", "One JSON object per log line (CloudWatch-friendly)"],
], col_widths=[2.6, 3.7], size=11, row_h=0.55)
table(s, Inches(7.2), Inches(1.5), Inches(5.5), [
    ["Endpoint", "Purpose"],
    ["GET /", "Demo chat UI (static/index.html)"],
    ["GET /health", "Config summary + index size"],
    ["POST /chat", "Main JSON API"],
    ["GET /ping", "AgentCore health contract"],
    ["POST /invocations", "AgentCore invoke contract; session header → thread_id"],
    ["GET /docs", "Auto-generated OpenAPI (FastAPI)"],
], col_widths=[1.8, 3.7], size=12, row_h=0.5)

# ------------------------------------------------- worked example --------
s = new_slide("Worked example: “Why was claim CLM-10002 denied?”", "Member M1001 · how the state evolves node by node",
              notes="This is the best end-to-end explanation: two agents collaborate. The claims agent finds a PA-01 denial and "
                    "hands a targeted query to the policy RAG agent, which explains prior authorization and the appeal process.")
table(s, Inches(0.6), Inches(1.45), Inches(12.1), [
    ["Step", "State change"],
    ["service.ask", "sanitize → no PII; initial_turn_state(); thread_id = session"],
    ["input_guard", "no injection → guardrail.blocked = False; messages += HumanMessage"],
    ["supervisor", "intent = claim_status; claim_id = CLM-10002 (regex); standalone_question set"],
    ["claims_agent", "get_claim(CLM-10002, M1001) ✔ owner → claim = {status: Denied, denial_code: PA-01}; search_query = 'PA-01 … appeal'"],
    ["after_claims", "denial_code present → retrieve"],
    ["retrieve → grade", "4 chunks ≥ 0.50 (prior authorization, appeals) → grader keeps 2"],
    ["generate", "'Claim CLM-10002 (MRI - lumbar spine, 2026-09-02): Denied [CLAIM]. Your responsibility: $0.00. Reason (PA-01)…' + cited explanation [1][2]"],
    ["groundedness_check", "every $ / % / deadline found in context → grounded = True"],
    ["output_guard → finalize", "no PII to redact → AIMessage saved; response: intent, citations, trace, latency"],
], col_widths=[2.3, 9.8], size=11, row_h=0.47)

# ------------------------------------------------- triggering RAG --------
s = new_slide("Triggering the RAG pipeline", "Indexing once, then query through any entry point",
              notes="Show the curl call live if time permits; the trace field shows exactly which nodes ran.")
code_box(s, Inches(0.6), Inches(1.9), Inches(6.0), Inches(2.1), """
# 1) Build / refresh the index
python -m app.ingest --reset
# 2) Start the API + UI
python -m app.api        # http://localhost:8080
""", size=13, title="Index + serve")
code_box(s, Inches(0.6), Inches(3.75), Inches(6.0), Inches(2.3), """
Invoke-RestMethod http://localhost:8080/chat `
  -Method Post -ContentType "application/json" `
  -Body '{"question": "Why was claim CLM-10002 denied?",
          "member_id": "M1001", "session_id": "demo-1"}'
""", size=12, title="HTTP (PowerShell)")
code_box(s, Inches(6.9), Inches(1.9), Inches(5.8), Inches(2.6), """
from app.service import AgentService, ChatRequest

svc = AgentService.from_settings()
r = svc.ask(ChatRequest(
        question="What is the Gold PPO deductible?",
        member_id="M1001", session_id="demo-1"))
print(r.answer, r.citations, r.trace)
""", size=12, title="Python (in-process)")
code_box(s, Inches(6.9), Inches(4.75), Inches(5.8), Inches(1.8), """
# AgentCore contract (local or deployed)
POST /invocations
{"prompt": "What is the Gold PPO deductible?",
 "member_id": "M1001"}
""", size=12, title="AgentCore payload")

# ------------------------------------------------- evaluation pipeline ---
s = new_slide("Evaluation pipeline (eval/run_eval.py)", "python -m eval.run_eval [--no-judge] [--limit N]  ·  exit code 1 = quality gate failed",
              notes="The harness calls the same AgentService as production, then reads the final graph state to score retrieval "
                    "(which chunks were used), not just the answer text.")
steps = [("golden_dataset.jsonl", "21 cases + expectations"), ("load_dataset()", "parse JSONL, --limit"),
         ("evaluate_case()", "service.ask() +\ngraph.get_state()"), ("judge()", "optional LLM-as-judge\nJudgeScore 1-5"),
         ("summarize()", "metrics + QUALITY_GATES"), ("write_reports()", "latest.json / latest.md\nexit 0 | 1")]
for i, (t, d) in enumerate(steps):
    x = Inches(0.5 + i * 2.1)
    box(s, x, Inches(1.65), Inches(1.85), Inches(1.05), f"{t}\n{d}", size=11, bold=True)
    if i:
        arrow(s, x - Inches(0.25), Inches(2.17), x, Inches(2.17))
table(s, Inches(0.6), Inches(3.1), Inches(7.4), [
    ["Metric (per case → summary)", "How it's computed"],
    ["intent_correct → intent_accuracy", "resp.intent == expected_intent"],
    ["retrieval_hit, reciprocal_rank → hit_rate, MRR", "expected source in state['documents'] (rank)"],
    ["keyword_recall", "share of expected facts ('$500', '180') in answer"],
    ["guardrail_correct → guardrail_accuracy", "blocked == should_block"],
    ["leakage_free / expected_flags_present", "must_not_contain absent; PII flag raised"],
    ["judge: faithfulness / relevance / correctness", "LLM scores vs. context + reference answer"],
    ["latency_p50 / p95", "wall-clock per case"],
], col_widths=[3.4, 4.0], size=11, row_h=0.45)
code_box(s, Inches(8.3), Inches(3.45), Inches(4.4), Inches(3.0), """
# fast, deterministic (CI on every PR)
python -m eval.run_eval --no-judge

# full, with LLM judge
python -m eval.run_eval

# stronger judge on Bedrock (.env)
EVAL_JUDGE_PROVIDER=bedrock
EVAL_JUDGE_MODEL=<claude profile id>
""", size=10, title="Commands")

# ------------------------------------------------- run commands ----------
s = new_slide("Commands: run locally and with Amazon Bedrock", "Same code; switch by editing .env",
              notes="Local is free and private; Bedrock mode can run from the laptop against cloud models before deploying "
                    "the container to AgentCore.")
code_box(s, Inches(0.6), Inches(1.9), Inches(6.0), Inches(4.9), """
# --- Local: Ollama + Chroma (Windows) ---
ollama pull llama3.2
ollama pull nomic-embed-text
cd agentic-rag-copilot
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements-dev.txt
copy .env.example .env

python -m app.ingest --reset   # index
python -m app.api              # :8080 UI+API
pytest                         # 74 tests
python -m eval.run_eval --no-judge
docker compose up --build      # containerised
""", size=12, title="Local")
code_box(s, Inches(6.9), Inches(1.9), Inches(5.8), Inches(4.9), """
# --- Bedrock: edit .env ---
LLM_PROVIDER=bedrock
AWS_REGION=us-east-1
BEDROCK_CHAT_MODEL_ID=<claude inference profile>
BEDROCK_EMBED_MODEL_ID=amazon.titan-embed-text-v2:0
RELEVANCE_THRESHOLD=0.35       # re-calibrate
GROUNDEDNESS_MODE=both

aws configure                  # or SSO
python -m app.ingest --reset   # Titan index
python -m app.api              # local app, cloud models
python -m eval.run_eval        # Claude judge

# --- Deploy to AgentCore Runtime ---
bash deploy/aws/deploy.sh
python deploy/aws/invoke_agentcore.py \\
    --arn <ARN> --prompt "Gold PPO deductible?"
""", size=12, title="Amazon Bedrock")

# ------------------------------------------------- tests -----------------
s = new_slide("Tests: how the graph is verified without a model", "74 tests in about 2 seconds, no Ollama / AWS: tests/conftest.py fakes",
              notes="Dependency injection pays off here: Deps takes any BaseChatModel and any KnowledgeBase, so tests swap in a "
                    "rule-based fake LLM and an in-memory KB and assert on the exact node trace.")
table(s, Inches(0.6), Inches(1.5), Inches(7.6), [
    ["File", "Covers"],
    ["conftest.py", "RuleBasedFakeLLM (answers by system prompt), FakeKB, make_service()"],
    ["test_guardrails.py", "PII detect/redact (Luhn), injection patterns, length, output allowlist"],
    ["test_graph.py", "Exact RAG trace, PII never persisted, injection skips LLM, authZ, fallback, regenerate loop, memory, numeric critic ($25 / 120 days), claim summary"],
    ["test_api.py", "/ping, /health, /chat, /invocations session header, 422 validation"],
], col_widths=[2.0, 5.6], size=11, row_h=0.7)
code_box(s, Inches(8.5), Inches(1.9), Inches(4.2), Inches(3.6), """
def test_policy_question_flows_through_rag(
        service):
    r = service.ask(ChatRequest(
        question="Gold PPO deductible?",
        member_id="M1001"))
    assert "$500" in r.answer
    assert r.grounded is True
    assert steps(r.trace) == [
      "input_guard", "supervisor",
      "retrieve", "grade", "generate",
      "groundedness", "output_guard",
      "finalize"]
""", size=10, title="Example")

# ------------------------------------------------- extending -------------
s = new_slide("Extending the framework", "How a client team adds capability without touching the core",
              notes="This is the 'reusable IP' story from the job description: new vertical = new documents + new tool node + "
                    "new golden cases.")
table(s, Inches(0.6), Inches(1.5), Inches(12.1), [
    ["I want to…", "Change", "Files"],
    ["Add or update policy documents", "Drop .md files into data/policies, run python -m app.ingest", "data/policies/"],
    ["Add a new agent / tool (e.g. provider finder)", "New AgentNodes method → g.add_node → route from supervisor; add intent to RouteDecision + SUPERVISOR_SYSTEM", "nodes.py, builder.py, state.py, prompts.py"],
    ["Use a different model", "Change OLLAMA_CHAT_MODEL / BEDROCK_CHAT_MODEL_ID", ".env"],
    ["Use a managed vector store", "VECTOR_BACKEND=bedrock_kb + BEDROCK_KB_ID", ".env"],
    ["Tighten safety", "Add INJECTION_PATTERNS / PII patterns; Bedrock topics and filters", "guardrails.py, create_guardrail.py"],
    ["Prove a change is better", "Add golden cases, run eval, compare latest.json with the previous report", "eval/"],
    ["Durable multi-instance memory", "CHECKPOINTER=sqlite locally; DynamoDB / AgentCore Memory saver in AWS", "builder.py"],
], col_widths=[3.4, 6.0, 2.7], size=12, row_h=0.58)
