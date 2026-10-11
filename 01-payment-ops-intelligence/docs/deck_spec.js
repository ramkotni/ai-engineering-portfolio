// Deck content for Payment Operations Intelligence. Build: cd tools/deck && node build.js ../../01-payment-ops-intelligence
const fs = require("fs");
const path = require("path");

const R = (f) => { try { return JSON.parse(fs.readFileSync(path.join(__dirname, "..", "eval", "results", f), "utf8")); } catch { return null; } };

module.exports = {
  fileName: "Payment_Ops_Intelligence.pptx",
  build(Deck) {
    const d = new Deck({
      title: "Payment Operations Intelligence",
      subtitle: "Multi-agent RCA, trends and recommendations for payment incidents - LangGraph, LangChain, ChromaDB, Ollama",
      footer: "Payment Operations Intelligence | portfolio prototype on synthetic data",
      accent: "F2A900",
    });
    const C = d.C;
    const ev = R("eval_report.json"), rg = R("ragas_report.json");

    d.cards("Context", "Why: payment investigations are slow and manual", [
      ["Scattered evidence", "Incident history in CSV exports, weekly monitoring reports in HTML, rules in a runbook."],
      ["Repeated RCA work", "Analysts re-investigate failures that already happened - duplicate wires, rejected ACH files, timeouts."],
      ["Leadership asks for trends", "Monthly counts, severity and MTTR are compiled by hand for every review."],
      ["Goal", "Ask in plain language: 'why', 'what should we do', 'is it getting worse', 'summarise for leadership' - with evidence."],
      ["Read-only by design", "The assistant analyses and recommends; it never releases, approves or edits payments."],
      ["Synthetic data", "60 fictional incidents (Apr-Sep 2026), 3 HTML reports, 1 runbook - planted trends to find."],
    ], { notes: "Independent re-implementation of a payment-operations intelligence pattern on synthetic data; not employer code or data." });

    d.custom("Architecture", "Architecture: supervisor + six specialist agents", (s) => {
      d.text(s, "Interfaces", { x: 0.6, y: 1.4, w: 2.3, h: 0.35, fontSize: 14, bold: true, color: C.accent5 });
      [["Streamlit UI", ":8501"], ["REST API", ":8001/docs"], ["CLI", "payops.cli"]].forEach(([t, c], i) => d.node(s, 0.6, 1.85 + i * 0.9, 2.3, 0.75, t, c));
      d.arrow(s, 2.95, 2.75, 3.3, 2.75);
      s.addShape(d.pres.shapes.ROUNDED_RECTANGLE, { x: 3.35, y: 1.4, w: 5.6, h: 3.9, rectRadius: 0.1, fill: { color: C.text2 }, line: { color: C.text2 } });
      d.text(s, [{ text: "LangGraph supervisor", options: { bold: true, fontSize: 16, color: C.background1, breakLine: true } },
        { text: "guard input -> Intent Agent -> RBAC -> plan -> agents -> guard output", options: { fontSize: 12, color: C.accent1 } }], { x: 3.6, y: 1.5, w: 5.2, h: 0.7 });
      [["Intent", "classify + filters"], ["Search", "hybrid retrieval"], ["RCA", "probable causes"], ["Recommend", "actions + rules"], ["Trend", "pandas + narrative"], ["Summary", "role-tailored"]]
        .forEach(([t, c], i) => d.node(s, 3.6 + (i % 3) * 1.75, 2.4 + Math.floor(i / 3) * 1.35, 1.6, 1.1, t, c, { fill: C.background1 }));
      d.text(s, "Models", { x: 9.3, y: 1.4, w: 3.4, h: 0.35, fontSize: 14, bold: true, color: C.accent5 });
      d.node(s, 9.3, 1.85, 3.4, 0.75, "Ollama llama3.2", "intent, RCA, recommendations, narrative");
      d.node(s, 9.3, 2.7, 3.4, 0.75, "nomic-embed-text", "embeddings");
      d.text(s, "Data", { x: 9.3, y: 3.6, w: 3.4, h: 0.35, fontSize: 14, bold: true, color: C.accent5 });
      d.node(s, 9.3, 4.0, 1.65, 0.75, "ChromaDB", "incidents | knowledge", { fill: C.accent4 });
      d.node(s, 11.05, 4.0, 1.65, 0.75, "pandas", "trend analytics", { fill: C.accent3 });
      d.arrow(s, 9.0, 2.6, 9.25, 2.6); d.arrow(s, 9.0, 4.35, 9.25, 4.35);
      d.text(s, "Ingestion", { x: 0.6, y: 5.5, w: 3, h: 0.35, fontSize: 14, bold: true, color: C.accent5 });
      [["incidents.csv", "1 doc per row"], ["reports/*.html", "-> Markdown"], ["runbook .md", "rules"], ["structure chunks", "sections, tables"], ["embed + store", "2 collections"]]
        .forEach(([t, c], i) => { d.node(s, 0.6 + i * 2.45, 5.9, 2.2, 0.8, t, c); if (i < 4) d.arrow(s, 2.82 + i * 2.45, 6.3, 3.03 + i * 2.45, 6.3); });
    }, { notes: "One service behind three interfaces. The supervisor graph runs only the agents a request needs; numbers come from pandas, text evidence from ChromaDB." });

    d.table("Architecture", "The agents and what each one does", [
      ["Agent", "Responsibility", "Tools / data", "LLM"],
      ["Intent", "Classify into RCA, Trend, Recommendation, Summary, Search + extract category, system, months", "Structured output, keyword fallback", "1 call"],
      ["Search", "Retrieve similar historical incidents and report/rule chunks", "ChromaDB hybrid (vector + BM25)", "none"],
      ["RCA", "Rank probable root causes from similar failures, citing incident IDs", "Search results", "1 call"],
      ["Recommendation", "Actions from past resolutions + business rules (PAY-RULES-001)", "Search results, rules collection", "1 call"],
      ["Trend", "Monthly counts, severity, MTTR, month-end share, rising categories", "pandas analytics", "narrates only"],
      ["Summary", "Executive or operational summary depending on the caller's role", "Trend output, recent Sev1/2, reports", "1 call"],
    ], { colW: [1.8, 5.0, 3.5, 1.8], notes: "Plans: search=[search]; rca=[search, rca (+recommendation)]; recommendation=[search, recommendation]; trend=[trend]; summary=[trend, summary]." });

    d.pipeline("RAG pipeline", "RAG pipeline and chunking", [
      ["CSV incidents", "each row = one chunk (symptom + cause + fix stay together)"],
      ["HTML reports", "BeautifulSoup -> Markdown: headings, lists, tables"],
      ["Structure chunker", "never crosses a section; tables kept whole; 800 chars"],
      ["Context header", "'Report title (ID) > Section' prefixed to every chunk"],
      ["nomic-embed-text", "task prefixes search_document / search_query"],
      ["ChromaDB + BM25", "hybrid, RRF fusion, metadata filters"],
    ], {
      below: (s) => {
        d.text(s, "Why row-level chunks for incidents: an incident is the unit of evidence - splitting it would separate the symptom from its root cause and resolution. Metadata (category, system, severity, month, amount) enables filtered search, e.g. only duplicate_payment incidents for an RCA about duplicates.",
          { x: 0.6, y: 3.5, w: 12.1, h: 1.0, fontSize: 15 });
        d.text(s, "Index: 60 incident documents + 19 report/rule chunks. The index stores a fingerprint of the embedding model and chunk settings and rebuilds itself when they change.",
          { x: 0.6, y: 4.7, w: 12.1, h: 0.8, fontSize: 14, color: C.accent5 });
      },
      notes: "Different sources get different chunking: tabular rows are already atomic, documents are chunked by structure.",
    });

    d.table("Security", "Sample roles (RBAC)", [
      ["Role", "Can run", "Amounts", "Summary style"],
      ["payment_analyst", "search, rca, recommendation, trend, summary", "visible", "operational"],
      ["operations_manager", "all", "visible", "operational"],
      ["executive", "trend, summary", "visible", "executive"],
      ["auditor", "search, trend, summary (no recommendations)", "visible", "operational"],
      ["support_engineer", "search, rca", "masked", "operational"],
    ], { colW: [2.6, 5.5, 1.6, 2.4], caption: "API: X-API-Key header -> role (demo keys in payops/roles.yaml). The authorize node denies intents a role may not run; amounts are masked in output for roles without financial visibility." });

    d.cards("Security", "Guardrails", [
      ["Read-only", "Commands to release, approve, cancel or re-send payments or change bank details are refused; questions about the process are answered."],
      ["Prompt injection", "Override / reveal-system-prompt patterns blocked before any LLM call."],
      ["Bank data + PII", "Account / routing numbers, emails and phones redacted in input and output."],
      ["Numeric grounding", "Every number in an answer must exist in the incidents, analytics or question."],
      ["Incident-ID grounding", "Cited PAY-INC IDs must be in the retrieved evidence - no invented incidents."],
      ["Role checks", "Intent permission + amount masking per role."],
    ], { notes: "All guardrails are deterministic and unit-tested; they run even when the LLM is unavailable." });

    const evRows = [["Area", "Metric", "Result"]];
    if (ev) {
      evRows.push(["Intent", `accuracy (${ev.intent.questions} questions, ${ev.intent.mode})`, `${Math.round(ev.intent.accuracy * 100)}%`]);
      evRows.push(["Retrieval", `hit@${ev.retrieval.top_k} / MRR / precision@${ev.retrieval.top_k}`, `${ev.retrieval.hit_rate} / ${ev.retrieval.mrr} / ${ev.retrieval.precision_at_k}`]);
      evRows.push(["Guardrails", `block precision / recall (${ev.guardrails.cases} cases)`, `${ev.guardrails.block_precision} / ${ev.guardrails.block_recall}`]);
      evRows.push(["Analytics", "category counts vs independent pandas", `${ev.analytics.passed}/${ev.analytics.checks}`]);
    }
    if (rg) {
      evRows.push(["RAGAS", "non-LLM context precision / recall (current config)", `${rg.baseline.context_precision} / ${rg.baseline.context_recall}`]);
      if (rg.llm_judged) {
        const f = rg.llm_judged.map((x) => x.faithfulness).filter((x) => x != null);
        evRows.push(["RAGAS (LLM judge)", `faithfulness on ${rg.llm_judged.length} end-to-end answers`, f.length ? (f.reduce((a, b) => a + b, 0) / f.length).toFixed(2) : "judge failed"]);
      }
    }
    d.table("Quality", "Evaluation results", evRows, { colW: [2.4, 6.5, 3.2], caption: "python -m eval.run_eval  |  python -m eval.ragas_eval --optimize --llm 3  |  python -m eval.langsmith_eval" });

    if (rg && rg.sweep) {
      d.table("Quality", "RAGAS-driven retrieval optimisation", [["Mode", "top_k", "Context precision", "Context recall", "F1"],
        ...rg.sweep.map((g) => [g.mode, g.top_k, g.context_precision, g.context_recall, g.f1])],
      { colW: [2.4, 1.6, 2.9, 2.9, 2.3], fontSize: 12, caption: `Recommended: ${rg.recommended.mode}, top_k=${rg.recommended.top_k}${rg.recommended.note ? " - " + rg.recommended.note : ""}. BM25-only is clearly worse; vector and hybrid tie on this corpus.` });
    }

    d.cards("Operations", "Monitoring", [
      ["LangSmith tracing", "Every agent, LLM call and retrieval traced with tags role:*, channel:*, provider:*."],
      ["Feedback", "UI buttons / POST /feedback attach user_rating to the LangSmith run."],
      ["Prometheus metrics", "GET /metrics: requests by intent/role/outcome, latency histogram, guardrail blocks, intent fallbacks."],
      ["Audit log", "logs/audit.jsonl: one line per question - role, intent, plan, citations, guardrails, latency."],
      ["Experiments", "eval/langsmith_eval.py runs the labelled set with evaluators in LangSmith."],
      ["Alerts to set", "p95 latency, denied/blocked rate, output-guardrail flags, negative feedback."],
    ]);

    d.codeSlide("Code", "Code: supervisor wiring (payops/graph.py)", [
      "PLANS = {",
      "  \"rca\": [\"search_agent\", \"rca_agent\"],",
      "  \"trend\": [\"trend_agent\"],",
      "  \"summary\": [\"trend_agent\", \"summary_agent\"], ...}",
      "",
      "g.add_conditional_edges(\"guard_input\", blocked_or_intent)",
      "g.add_edge(\"intent_agent\", \"authorize\")",
      "g.add_conditional_edges(\"supervisor\", next_step,",
      "    agent_nodes + [\"compose\"])",
      "for a in agent_nodes:",
      "    g.add_edge(a, \"supervisor\")",
      "g.add_edge(\"compose\", \"guard_output\")",
    ].join("\n"), [
      ["Plan per intent", "The Intent Agent picks the intent; authorize turns it into an ordered list of agents allowed for the role."],
      ["Supervisor loop", "Each agent returns to the supervisor, which routes to the next agent or to compose."],
      ["Shared state", "Agents write to state.outputs[name]; later agents read earlier outputs (RCA -> Recommendation)."],
      ["Fallbacks", "Every LLM agent has a deterministic fallback, so an outage degrades, not fails."],
    ]);

    d.custom("Run", "Run, test and monitor", (s) => {
      d.code(s, 0.6, 1.45, 12.1, null, [
        "cd 01-payment-ops-intelligence",
        "python data/generate_data.py            # optional: regenerate sample data",
        "python -m payops.ingest                 # build ChromaDB (nomic-embed-text)",
        "uvicorn payops.api:app --port 8001      # API  -> http://localhost:8001/docs",
        "streamlit run ui/streamlit_app.py --server.port 8501   # UI -> http://localhost:8501",
        "",
        "curl -X POST localhost:8001/ask -H \"X-API-Key: analyst-demo-key\" -H \"Content-Type: application/json\" \\",
        "     -d '{\"question\": \"Why are vendors being paid twice and what should we do?\"}'",
        "curl localhost:8001/metrics             # Prometheus metrics",
        "",
        "pytest -q                               # 28 tests, no model needed",
        "python -m eval.run_eval                 # intent / retrieval / guardrails / analytics",
        "python -m eval.ragas_eval --optimize    # RAGAS + retrieval sweep",
      ].join("\n"), 13);
    });

    d.table("Run", "Tech stack", [
      ["Layer", "Technology"],
      ["Agents / orchestration", "LangGraph 1.2 (supervisor pattern), LangChain core 1.6"],
      ["Models", "Ollama llama3.2 (chat), nomic-embed-text (embeddings); Bedrock optional"],
      ["Retrieval", "ChromaDB 1.5 + in-process BM25 (reciprocal rank fusion)"],
      ["Analytics", "pandas"],
      ["Ingestion", "csv, BeautifulSoup (HTML), structure-aware chunker"],
      ["Serving", "FastAPI, Streamlit"],
      ["Quality / monitoring", "pytest, RAGAS 0.4.3, LangSmith, Prometheus-format /metrics"],
    ], { colW: [3.2, 8.9] });

    d.closing("Next steps", [
      "Connect to live incident exports and monitoring reports (scheduled ingestion)",
      "Add a ticketing tool to the Recommendation Agent (create follow-up tasks, still human-approved)",
      "Multi-turn investigations with a LangGraph checkpointer",
      "LLM-judged RAGAS on Bedrock/Claude as a CI quality gate",
    ]);
    return d;
  },
};
