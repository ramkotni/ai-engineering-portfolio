// Deck for the Supply Chain Knowledge Assistant.  cd tools/deck && node build.js ../../03-supply-chain-knowledge-assistant
const fs = require("fs");
const path = require("path");

const R = (f) => { try { return JSON.parse(fs.readFileSync(path.join(__dirname, "..", "eval", "results", f), "utf8")); } catch { return null; } };
const IMG = (f) => path.join(__dirname, "..", "data", "extracted", "images", f);

module.exports = {
  fileName: "Supply_Chain_Knowledge_Assistant.pptx",
  build(Deck) {
    const d = new Deck({
      title: "Supply Chain Knowledge Assistant",
      subtitle: "Multimodal RAG over PDF, Word, HTML, CSV and extracted figures - Llama over REST, LangGraph, ChromaDB",
      footer: "Supply Chain Knowledge Assistant | portfolio prototype on synthetic data",
      accent: "2E9E6B",
    });
    const C = d.C;
    const ev = R("eval_report.json"), rg = R("ragas_report.json");

    d.cards("Context", "Why: controlled knowledge is locked in documents and figures", [
      ["Many formats", "SOPs as PDF, deviations in Word, supplier status in HTML, lot data in CSV."],
      ["Answers hide in figures", "Decision flowcharts, network maps and logger charts carry facts found nowhere in text."],
      ["Access is regulated", "Confidential deviations must not reach partners or the wrong teams."],
      ["Slow root-cause work", "Investigators read whole documents to find one excursion rule or lot status."],
      ["Goal", "Ask, summarise or search across all formats - with citations, figures and clearance enforced."],
      ["Integration", "Llama-based model behind REST APIs so enterprise apps can call it."],
    ]);

    d.pipeline("RAG pipeline", "Ingestion: every format to Markdown, figures to captions", [
      ["PDF", "pdfplumber text + tables, font-size headings; PyMuPDF images"],
      ["Word", "heading styles, tables, inline pictures in order"],
      ["HTML / MD / CSV", "BeautifulSoup; rows -> records"],
      ["Image markers", "[[IMAGE:id]] kept where the figure appears"],
      ["Vision captions", "gemma3:4b transcribes + describes; cached by hash"],
      ["Chunks + embed", "text | table | image | record -> nomic -> ChromaDB"],
    ], {
      below: (s) => {
        d.text(s, "Each figure becomes its own 'image' chunk under the section heading where it appeared, so a question about the excursion flowchart cites 'SOP-CC-001 > Monitoring' and the UI shows the figure. Chunks never cross sections; tables stay whole up to 2,500 chars; CSV rows are one chunk each; every chunk carries its document classification.",
          { x: 0.6, y: 3.45, w: 12.1, h: 1.2, fontSize: 15 });
        d.text(s, "50 chunks: 14 text, 2 table, 1 mixed, 3 image, 30 record.", { x: 0.6, y: 4.8, w: 12.1, h: 0.5, fontSize: 14, color: C.accent5 });
      },
    });

    d.custom("RAG pipeline", "Image extraction: a figure becomes searchable", (s) => {
      if (fs.existsSync(IMG("SOP-CC-001_p1_img1.png"))) s.addImage({ path: IMG("SOP-CC-001_p1_img1.png"), x: 0.6, y: 1.45, w: 6.2, h: 4.29 });
      d.card(s, 7.1, 1.45, 5.6, 4.3);
      let cap = "";
      try { cap = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "extracted", "captions.json"), "utf8"))["SOP-CC-001_p1_img1"].caption; } catch { cap = ""; }
      d.text(s, [{ text: "Vision caption (gemma3:4b, cached)", options: { bold: true, fontSize: 14, breakLine: true } },
        { text: (cap || "run python -m supplykb.vision").split("**").join("").split(String.fromCharCode(10)).filter((l) => l.trim() && !/^(okay|sure|here)/i.test(l.trim())).join(String.fromCharCode(10)).slice(0, 430), options: { fontSize: 11 } }], { x: 7.3, y: 1.6, w: 5.2, h: 4.0 });
      d.text(s, "Extracted from page 1 of SOP-CC-001 (PDF) with PyMuPDF, captioned once, embedded as an 'image' chunk. Question: 'What should happen if a 2-8 C product is above 8 C for more than 2 hours?' is answered from this figure.",
        { x: 0.6, y: 6.0, w: 12.1, h: 0.8, fontSize: 13, color: C.accent5 });
    });

    d.custom("Architecture", "Single-agent RAG workflow (LangGraph)", (s) => {
      const steps = [["guard_input", "injection, medical, actions"], ["classify_task", "qa | summarize | search"], ["authorize", "task + clearance"],
        ["retrieve", "clearance filter first"], ["grade", "relevance floor"], ["generate", "prompt template v1"], ["verify", "numbers + IDs"]];
      steps.forEach(([t, c], i) => { d.node(s, 0.6 + i * 1.75, 1.7, 1.55, 1.1, t, c); if (i < 6) d.arrow(s, 2.17 + i * 1.75, 2.25, 2.33 + i * 1.75, 2.25, { color: C.accent1 }); });
      d.text(s, "Why a single agent: one knowledge domain and three tasks - a multi-agent design would add LLM calls and nondeterminism without new capability. Search needs no LLM at all; QA and summaries use one call each with versioned ChatPromptTemplates (qa/v1, summarize/v1 brief | detailed | executive).",
        { x: 0.6, y: 3.2, w: 12.1, h: 1.1, fontSize: 15 });
      d.text(s, "REST endpoints for enterprise integration: POST /ask, /summarize, /search; GET /documents (clearance-filtered), /images/{id} (403 if not cleared), /metrics, /roles.",
        { x: 0.6, y: 4.5, w: 12.1, h: 0.8, fontSize: 14, color: C.accent5 });
    });

    d.table("Security", "Sample roles and document clearance", [
      ["Role", "Clearance", "Tasks"],
      ["supply_planner", "internal", "qa, search, summarize"],
      ["quality_assurance", "confidential", "qa, search, summarize"],
      ["regulatory_affairs", "confidential", "qa, search, summarize"],
      ["logistics_partner", "public", "qa, search"],
    ], { colW: [3.5, 3.0, 5.6], caption: "Classification (public < internal < confidential) is applied as a retrieval filter before ranking - restricted text never reaches the prompt." });

    d.cards("Security", "Guardrails", [
      ["Medical advice", "Dosing / patient-use questions refused - supply-chain answers only."],
      ["QA decisions", "Release / reject / quarantine / recall commands refused; procedures explained."],
      ["Access control", "Clearance filter before retrieval; image and summary endpoints check classification."],
      ["Grounding", "Numbers and LOT- / SHP- / DEV- / SOP- / CAPA- IDs must appear in retrieved context."],
      ["Injection + PII", "Override attempts blocked; emails / phones redacted."],
      ["No guessing", "Nothing relevant -> 'The documents I can access do not cover this.'"],
    ]);

    const rows = [["Metric", "Result"]];
    if (ev) {
      rows.push([`Retrieval hit@${ev.retrieval.top_k} / MRR (${ev.retrieval.questions} questions)`, `${ev.retrieval.hit_rate} / ${ev.retrieval.mrr}`]);
      Object.entries(ev.retrieval.by_source_type).forEach(([t, v]) => rows.push([`hit rate - ${t} questions`, String(v)]));
      rows.push(["Image chunk retrieved for figure questions", String(ev.retrieval.image_chunk_retrieved_for_figure_questions)]);
      rows.push(["Restricted chunks returned to logistics_partner", String(ev.access_control.restricted_chunks_returned_to_partner)]);
      rows.push([`Guardrails precision / recall (${ev.guardrails.cases})`, `${ev.guardrails.block_precision} / ${ev.guardrails.block_recall}`]);
    }
    if (rg) rows.push(["RAGAS non-LLM context precision / recall", `${rg.baseline.context_precision} / ${rg.baseline.context_recall}`]);
    if (rg && rg.llm_judged) rg.llm_judged.forEach((x) => rows.push([`RAGAS LLM-judged: ${x.question.slice(0, 48)}`, `faith ${x.faithfulness ?? "n/a"} | grounded ${x.response_groundedness ?? "n/a"} | recall ${x.llm_context_recall ?? "n/a"}`]));
    d.table("Quality", "Evaluation results", rows, { colW: [7.6, 4.5], fontSize: 12 });
    if (rg && rg.sweep) {
      d.table("Quality", "RAGAS-driven retrieval optimisation", [["Mode", "top_k", "Context precision", "Context recall", "F1"],
        ...rg.sweep.map((g) => [g.mode, g.top_k, g.context_precision, g.context_recall, g.f1])],
      { colW: [2.4, 1.6, 2.9, 2.9, 2.3], fontSize: 12, caption: `Recommended: ${rg.recommended.mode}, top_k=${rg.recommended.top_k}${rg.recommended.note ? " - " + rg.recommended.note : ""}` });
    }
    d.cards("Operations", "Monitoring", [
      ["LangSmith", "traces of retrieval and generation; tags role / channel; feedback as user_rating"],
      ["/metrics", "supplykb_requests_total{intent,role,outcome}, latency histogram, guardrail blocks"],
      ["Audit log", "logs/audit.jsonl - question, task, citations, guardrails, latency"],
    ], { cols: 3 });
    d.custom("Run", "Run and test", (s) => d.code(s, 0.6, 1.45, 12.1, null, [
      "cd 03-supply-chain-knowledge-assistant",
      "ollama pull gemma3:4b                       # vision model for captions",
      "python -m supplykb.vision                   # caption extracted figures (cached)",
      "python -m supplykb.ingest                   # 50 chunks",
      "uvicorn supplykb.api:app --port 8003        # http://localhost:8003/docs",
      "streamlit run ui/streamlit_app.py --server.port 8503",
      "pytest -q                                   # 18 tests",
      "python -m eval.run_eval                     # hit@k by source type, leakage, guardrails",
      "python -m eval.ragas_eval --optimize --llm 2",
    ].join("\n"), 13));
    d.closing("Next steps", [
      "Connect to the document management system with revision-aware re-ingestion",
      "OCR for scanned PDFs; richer chart extraction (data series)",
      "Department-level access groups on top of clearance",
      "Stronger judge model for LLM-judged RAGAS in CI",
    ]);
    return d;
  },
};
