// Deck for the Robotics Fleet Assistant.  cd tools/deck && node build.js ../../02-robotics-fleet-assistant
const fs = require("fs");
const path = require("path");

const R = (f) => { try { return JSON.parse(fs.readFileSync(path.join(__dirname, "..", "eval", "results", f), "utf8")); } catch { return null; } };

module.exports = {
  fileName: "Robotics_Fleet_Assistant.pptx",
  build(Deck) {
    const d = new Deck({
      title: "Robotics Fleet Assistant",
      subtitle: "Multi-agent diagnostics, predictive maintenance and task optimisation for warehouse robots - LangGraph, LangChain, ChromaDB",
      footer: "Robotics Fleet Assistant | portfolio prototype on synthetic data",
      accent: "2D7DD2",
    });
    const C = d.C;
    const ev = R("eval_report.json"), rg = R("ragas_report.json");

    d.cards("Context", "Why: keeping a robot fleet productive is reactive today", [
      ["Failures diagnosed one by one", "Battery, sensor, motor, scanner, Wi-Fi and navigation faults look alike on the console."],
      ["Maintenance is calendar-based", "Packs fail before the next PM while healthy robots get serviced early."],
      ["Uneven workload", "Some robots queue 14 tasks while others in the same zone sit idle."],
      ["Daily reports by hand", "Shift leads compile fleet health, incidents and risks manually."],
      ["Goal", "One assistant: diagnose, predict, rebalance and summarise - with evidence and numbers from data."],
      ["Safety first", "Never bypass safety systems; advisory only - people execute changes in the fleet console."],
    ], { color: C.accent1 });

    d.custom("Architecture", "Architecture: supervisor + eight agents", (s) => {
      s.addShape(d.pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.4, w: 8.3, h: 4.0, rectRadius: 0.1, fill: { color: C.text2 }, line: { color: C.text2 } });
      d.text(s, [{ text: "LangGraph supervisor", options: { bold: true, fontSize: 16, color: C.background1, breakLine: true } },
        { text: "guard input -> Intent -> authorize (role intents + zones) -> plan -> agents -> guard output", options: { fontSize: 12, color: C.accent1 } }],
      { x: 0.85, y: 1.5, w: 7.9, h: 0.7 });
      [["Intent", "7 workflows + slots"], ["Fleet Search", "hybrid RAG"], ["Diagnostics", "probable causes"], ["Battery", "health slope"],
        ["Predictive Maint.", "risk score"], ["Task Optimization", "rebalancing"], ["Fleet Status", "per zone"], ["Ops Summary", "daily report"]]
        .forEach(([t, c], i) => d.node(s, 0.85 + (i % 4) * 2.0, 2.45 + Math.floor(i / 4) * 1.4, 1.85, 1.15, t, c, { fill: C.background1 }));
      d.text(s, "Data and models", { x: 9.3, y: 1.4, w: 3.4, h: 0.35, fontSize: 14, bold: true, color: C.accent5 });
      d.node(s, 9.3, 1.85, 3.4, 0.75, "ChromaDB", "events (incidents + maintenance) | guide", { fill: C.accent4 });
      d.node(s, 9.3, 2.75, 3.4, 0.75, "pandas / numpy", "battery slope, risk, rebalancing", { fill: C.accent3 });
      d.node(s, 9.3, 3.65, 3.4, 0.75, "Ollama", "llama3.2 + nomic-embed-text");
      d.node(s, 9.3, 4.55, 3.4, 0.75, "Interfaces", "API :8002 | UI :8502 | CLI");
      d.text(s, "Plans: diagnostics = [search, diagnostics]; predictive maintenance = [battery, maintenance]; task assignment = [fleet status, task optimization]; summary = [status, battery, maintenance, summary]. Only the final agent calls the LLM for narrative.",
        { x: 0.6, y: 5.7, w: 12.1, h: 0.9, fontSize: 14 });
    });

    d.table("Architecture", "Agents", [
      ["Agent", "Job", "Data / tools", "LLM"],
      ["Intent", "7 workflows; extract robot ID, zone, event type", "structured output + keyword fallback", "1 call"],
      ["Fleet Search", "similar incidents and maintenance records; guide sections", "ChromaDB hybrid + metadata filters", "none"],
      ["Robot Diagnostics", "probable cause: battery, sensor, motor, scanner, Wi-Fi, navigation", "robot record, events, guide", "1 call"],
      ["Battery Analysis", "30-day health slope vs replacement policy", "battery_telemetry + numpy polyfit", "narrates"],
      ["Predictive Maintenance", "risk score from health, cycles, PM age, incidents", "pandas + policy chunks", "narrates"],
      ["Task Optimization", "move tasks from overloaded to under-used healthy robots in the same zone", "pandas rules", "narrates"],
      ["Fleet Status", "status and utilisation per zone", "pandas", "none"],
      ["Operations Summary", "daily health report for ops or executives", "all agent outputs", "1 call"],
    ], { colW: [2.3, 4.6, 3.5, 1.7], fontSize: 12 });

    d.pipeline("RAG pipeline", "RAG pipeline and chunking", [
      ["incidents.csv", "1 doc per event: symptom, cause, fix"],
      ["maintenance_logs.csv", "1 doc per action"],
      ["troubleshooting guide", "sections; error-code table kept whole"],
      ["metadata", "robot, zone, firmware, event type, code"],
      ["nomic-embed-text", "-> ChromaDB events + knowledge"],
      ["hybrid search", "vector + BM25, filters, zone scope"],
    ], {
      below: (s) => d.text(s, "Rows are already atomic units of evidence, so CSV records are not split. The guide is chunked by section (700 chars) and its error-code table is one chunk - splitting a table mid-row would separate a code from its fix. Filters narrow retrieval to the robot, event type or the caller's zones before ranking.",
        { x: 0.6, y: 3.5, w: 12.1, h: 1.4, fontSize: 15 }),
    });

    d.table("Security", "Sample roles and zone scope", [
      ["Role", "Can run", "Zones"],
      ["technician", "diagnostics, navigation, battery, predictive maintenance, fleet status", "all"],
      ["shift_lead", "fleet status, task assignment, summary, diagnostics, navigation", "all"],
      ["fleet_manager", "all seven workflows", "all"],
      ["site_executive", "summary (executive style), fleet status", "all"],
      ["contractor_technician", "diagnostics, battery, navigation", "Z1-Inbound only"],
    ], { colW: [2.8, 7.0, 2.3], caption: "X-API-Key -> role. Zone scope is enforced in authorize (robot outside zone -> denied), in retrieval filters and in analytics." });

    d.cards("Security", "Guardrails", [
      ["Safety overrides", "Disable/bypass e-stop, lidar, bumpers, safety fields, collision avoidance -> refused."],
      ["Restricted zones", "Requests to drive robots into human-only or restricted zones -> refused."],
      ["Advisory only", "Commands to dispatch, reassign, reboot or push firmware -> refused; recommendations allowed."],
      ["Grounded output", "Numbers from analytics only; robot / event / maintenance IDs must exist in the evidence."],
      ["Unsafe advice filter", "Generated answers suggesting safety bypasses are withheld."],
      ["Slot grounding", "Robot IDs, zones and event types must appear in the question."],
    ], { color: C.accent1 });

    const rows = [["Area", "Metric", "Result"]];
    if (ev) {
      rows.push(["Intent", `accuracy (${ev.intent.questions} questions, ${ev.intent.mode})`, `${Math.round(ev.intent.accuracy * 100)}%`]);
      rows.push(["Retrieval", `hit@${ev.retrieval.top_k} / MRR / precision@${ev.retrieval.top_k} (event type)`, `${ev.retrieval.hit_rate} / ${ev.retrieval.mrr} / ${ev.retrieval.precision_at_k}`]);
      rows.push(["Guardrails", `block precision / recall (${ev.guardrails.cases} cases)`, `${ev.guardrails.block_precision} / ${ev.guardrails.block_recall}`]);
      rows.push(["Analytics", "fast battery decline robots found", ev.analytics.fast_battery_decline_correct ? "3 / 3 correct" : ev.analytics.fast_battery_decline_found.join(", ")]);
      rows.push(["Analytics", "rebalancing", `${ev.analytics.rebalance_tasks_moved} tasks -> ${ev.analytics.rebalance_targets_underused.join(", ")}`]);
    }
    if (rg) rows.push(["RAGAS", "non-LLM context precision / recall", `${rg.baseline.context_precision} / ${rg.baseline.context_recall}`]);
    d.table("Quality", "Evaluation results", rows, { colW: [2.2, 6.6, 3.3] });
    if (rg && rg.sweep) {
      d.table("Quality", "RAGAS-driven retrieval optimisation", [["Mode", "top_k", "Context precision", "Context recall", "F1"],
        ...rg.sweep.map((g) => [g.mode, g.top_k, g.context_precision, g.context_recall, g.f1])],
      { colW: [2.4, 1.6, 2.9, 2.9, 2.3], fontSize: 12, caption: `Recommended: ${rg.recommended.mode}, top_k=${rg.recommended.top_k}${rg.recommended.note ? " - " + rg.recommended.note : ""}` });
    }

    d.cards("Operations", "Monitoring", [
      ["LangSmith", "Traces of every agent and LLM call; tags role, channel, provider; feedback as user_rating."],
      ["/metrics", "fleetops_requests_total{intent,role,outcome}, latency histogram, guardrail blocks, fallbacks."],
      ["Audit log", "logs/audit.jsonl per question and feedback."],
    ], { cols: 3 });

    d.custom("Run", "Run, test and monitor", (s) => d.code(s, 0.6, 1.45, 12.1, null, [
      "cd 02-robotics-fleet-assistant",
      "python -m fleetops.ingest                       # build ChromaDB",
      "uvicorn fleetops.api:app --port 8002            # http://localhost:8002/docs",
      "streamlit run ui/streamlit_app.py --server.port 8502",
      "curl -X POST localhost:8002/ask -H \"X-API-Key: tech-demo-key\" \\",
      "     -H \"Content-Type: application/json\" -d '{\"question\": \"Why does R-1007 keep stopping?\"}'",
      "",
      "pytest -q                                       # 25 tests",
      "python -m eval.run_eval                         # intent / retrieval / guardrails / analytics",
      "python -m eval.ragas_eval --optimize            # RAGAS + sweep",
    ].join("\n"), 13));

    d.closing("Next steps", [
      "Stream live telemetry and fleet-console events into the index",
      "Feed technician feedback into the risk-score weights",
      "Approval workflow: shift lead accepts a proposed rebalance in one click",
      "Multi-site roll-out with per-site zone scopes",
    ]);
    return d;
  },
};
