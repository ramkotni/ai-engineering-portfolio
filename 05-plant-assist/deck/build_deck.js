// Builds docs/PlantAssist_Architecture.pptx
//   cd deck && npm install && node build_deck.js
// Evaluation numbers are read from ../eval/results.json when present (python -m eval.run_eval).

const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
const { applyTheme } = require("./apply_theme.js");

const OUT = process.env.DECK_OUT || path.join(__dirname, "..", "docs", "PlantAssist_Architecture.pptx");
const EVAL = path.join(__dirname, "..", "eval", "results.json");

const THEME = {
  name: "PlantAssist Industrial",
  headFontFace: "Arial",
  bodyFontFace: "Calibri",
  colors: {
    dk1: "1B2430", // graphite text
    lt1: "FFFFFF",
    dk2: "24303D", // dark steel (title / closing background, code cards)
    lt2: "EEF1F4", // light steel (cards)
    accent1: "F2A900", // safety amber - brand accent
    accent2: "D64933", // safety source
    accent3: "2D7DD2", // maintenance source
    accent4: "2E9E6B", // quality source
    accent5: "6B7785", // muted slate
    accent6: "7A5CC4", // LangGraph / control flow
    hlink: "2D7DD2",
    folHlink: "7A5CC4",
  },
};
const HEX = THEME.colors;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.333 x 7.5 in
pres.title = "PlantAssist - Architecture and Flow";
pres.author = "PlantAssist prototype";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
const SRC = { safety: C.accent2, maintenance: C.accent3, quality: C.accent4 };
const MONO = "Courier New";

// ---------------------------------------------------------------- layouts
pres.defineSlideMaster({
  title: "TITLE_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.2, w: 11.7, h: 1.4, fontSize: 54, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.8, y: 3.75, w: 11.7, h: 0.9, fontSize: 24, color: C.accent1, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CLOSING_DARK",
  background: { color: C.text2 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 0.7, w: 11.7, h: 1.1, fontSize: 48, bold: true, color: C.background1, align: "left", valign: "bottom", margin: 0 }, text: "" } },
    { placeholder: { options: { name: "subtitle", type: "body", x: 0.8, y: 1.9, w: 11.7, h: 0.6, fontSize: 22, color: C.accent1, align: "left", valign: "top", margin: 0 }, text: "" } },
  ],
});
pres.defineSlideMaster({
  title: "CONTENT",
  background: { color: C.background1 },
  objects: [
    { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 36, bold: true, color: C.text1, align: "left", valign: "middle", margin: 0 }, text: "" } },
    { text: { text: "PlantAssist prototype  |  Architecture and flow", options: { x: 0.6, y: 7.0, w: 6, h: 0.3, fontSize: 10, color: C.accent5, margin: 0 } } },
  ],
  slideNumber: { x: 12.2, y: 7.0, w: 0.5, h: 0.3, fontSize: 10, color: C.accent5, align: "right" },
});

// ---------------------------------------------------------------- helpers
const text = (slide, t, o) => slide.addText(t, { isTextBox: true, margin: 0, valign: "top", fontSize: 14, color: C.text1, ...o });

function card(slide, x, y, w, h, fill = C.background2, name) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill }, objectName: name });
}

function badge(slide, x, y, d, label, fill, fontSize = 16) {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
  text(slide, label, { x, y, w: d, h: d, align: "center", valign: "middle", bold: true, fontSize, color: C.background1 });
}

function arrow(slide, x1, y1, x2, y2, { color = C.accent5, dash = "solid", width = 1.75, head = true } = {}) {
  slide.addShape(pres.shapes.LINE, {
    x: Math.min(x1, x2), y: Math.min(y1, y2), w: Math.max(Math.abs(x2 - x1), 0.001), h: Math.max(Math.abs(y2 - y1), 0.001),
    flipH: x2 < x1, flipV: y2 < y1,
    line: { color, width, dashType: dash, endArrowType: head ? "triangle" : undefined },
  });
}

function node(slide, x, y, w, h, title, caption, { fill = C.background2, titleColor = C.text1, captionColor = C.accent5, outline } = {}) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: outline || fill, width: outline ? 1.5 : 0.75 } });
  const runs = [{ text: title, options: { bold: true, fontSize: 14, color: titleColor, breakLine: !!caption } }];
  if (caption) runs.push({ text: caption, options: { fontSize: 11, color: captionColor } });
  text(slide, runs, { x: x + 0.08, y, w: w - 0.16, h, align: "center", valign: "middle" });
}

function contentSlide(section, title) {
  const s = pres.addSlide({ masterName: "CONTENT", sectionTitle: section });
  s.addText(title, { placeholder: "title" });
  return s;
}

// ---------------------------------------------------------------- 1. title
pres.addSection({ title: "Context" });
{
  const s = pres.addSlide({ masterName: "TITLE_DARK", sectionTitle: "Context" });
  s.addText("PlantAssist", { placeholder: "title" });
  s.addText("Routing floor-supervisor questions to the right plant documentation", { placeholder: "subtitle" });
  const chips = [["Safety procedures", C.accent2], ["Maintenance manuals", C.accent3], ["Quality standards", C.accent4]];
  chips.forEach(([label, color], i) => {
    const x = 0.8 + i * 2.95;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 5.0, w: 2.75, h: 0.55, rectRadius: 0.27, fill: { color }, line: { color } });
    text(s, label, { x, y: 5.0, w: 2.75, h: 0.55, align: "center", valign: "middle", bold: true, fontSize: 15, color: C.background1 });
  });
  text(s, "Prototype architecture and flow  |  Python, LangGraph, LangChain  |  Ollama locally, AWS Bedrock in production", { x: 0.8, y: 6.3, w: 11.7, h: 0.4, fontSize: 14, color: C.background2 });
  s.addNotes("PlantAssist is a prototype assistant that lets floor supervisors ask plain-language questions and get cited answers from the right documentation set: safety procedures, maintenance manuals or quality control standards. It runs fully locally on Ollama and moves to AWS Bedrock with a configuration change.");
}

// ---------------------------------------------------------------- 2. problem
{
  const s = contentSlide("Context", "Supervisors need one trusted answer, fast");
  text(s, "Today: three separate documentation silos", { x: 0.6, y: 1.45, w: 5.9, h: 0.4, fontSize: 18, bold: true, color: C.accent5 });
  const silos = [
    ["S", C.accent2, "Safety procedures", "LOTO, PPE, chemical spills, emergency response", "\"Someone spilled solvent near line 3 - what now?\""],
    ["M", C.accent3, "Maintenance manuals", "Hydraulic press, CNC, conveyor, compressor", "\"What torque for the press gland bolts?\""],
    ["Q", C.accent4, "Quality control standards", "Sampling, SPC / Cpk, NCR and CAPA, calibration", "\"Eight points above the center line - problem?\""],
  ];
  silos.forEach(([letter, color, title, desc, q], i) => {
    const y = 2.0 + i * 1.6;
    card(s, 0.6, y, 5.9, 1.4);
    badge(s, 0.85, y + 0.32, 0.75, letter, color, 22);
    text(s, [
      { text: title, options: { bold: true, fontSize: 17, breakLine: true } },
      { text: desc, options: { fontSize: 14, color: C.accent5, breakLine: true } },
      { text: q, options: { fontSize: 14, italic: true } },
    ], { x: 1.85, y: y + 0.15, w: 4.5, h: 1.15, valign: "middle" });
  });

  text(s, "What supervisors need", { x: 7.1, y: 1.45, w: 5.6, h: 0.4, fontSize: 18, bold: true, color: C.accent5 });
  const needs = [
    ["Right source", "Each question routed to safety, maintenance or quality - or several when it spans domains."],
    ["Grounded and cited", "Every fact traceable to a document ID, revision and section."],
    ["Safety first", "Hands-on work always pulls lockout/tagout and PPE requirements."],
    ["Never guess", "If the documents do not cover it, say so and name the owner to call."],
  ];
  needs.forEach(([title, desc], i) => {
    const y = 2.05 + i * 1.2;
    badge(s, 7.1, y + 0.05, 0.55, String(i + 1), C.accent1, 16);
    text(s, [
      { text: title, options: { bold: true, fontSize: 17, breakLine: true } },
      { text: desc, options: { fontSize: 14, color: C.text1 } },
    ], { x: 7.9, y, w: 4.8, h: 1.05 });
  });
  s.addNotes("The plant keeps three bodies of documentation, each owned by a different team. Supervisors know their question, not which binder holds the answer. A wrong source is not just inconvenient: a maintenance answer that omits lockout/tagout is a safety risk. These four needs became the design requirements.");
}

// ---------------------------------------------------------------- 2b. business use case
{
  const s = contentSlide("Context", "Business case: faster, safer floor decisions");
  text(s, "Target outcomes for a pilot", { x: 0.6, y: 1.4, w: 12.1, h: 0.4, fontSize: 18, bold: true, color: C.accent5 });
  const kpis = [
    ["Seconds", "to the right procedure, instead of searching three binders or calling an engineer", C.accent1],
    ["100%", "of answers cite document ID, revision and section - an audit trail for every decision", C.accent6],
    ["Fewer calls", "to EHS, maintenance and quality engineers for routine questions", C.accent4],
  ];
  kpis.forEach(([big, label, color], i) => {
    const x = 0.6 + i * 4.1;
    text(s, big, { x, y: 1.85, w: 3.9, h: 0.85, fontSize: 44, bold: true, color, fontFace: THEME.headFontFace });
    text(s, label, { x, y: 2.7, w: 3.7, h: 0.75, fontSize: 14 });
  });

  const scenarios = [
    ["Breakdown on HP-200", "Seal replacement steps from the manual, with lockout/tagout pulled in automatically", "Shorter downtime; no missed energy isolation", C.accent3],
    ["Solvent spill on line 3", "Emergency banner first, then the major-spill response with the right extension", "Faster, compliant response; no improvising", C.accent2],
    ["SPC alarm on a CTQ", "Western Electric rule identified plus the containment and reaction plan", "Suspect parts held earlier; fewer escapes", C.accent4],
  ];
  scenarios.forEach(([title, what, value, color], i) => {
    const x = 0.6 + i * 4.1, y = 3.75;
    card(s, x, y, 3.85, 2.85);
    badge(s, x + 0.25, y + 0.25, 0.5, String(i + 1), color, 14);
    text(s, title, { x: x + 0.9, y: y + 0.25, w: 2.8, h: 0.5, fontSize: 16, bold: true, valign: "middle" });
    text(s, [
      { text: "PlantAssist: ", options: { bold: true } }, { text: what, options: { breakLine: true } },
      { text: "Value: ", options: { bold: true, color: color } }, { text: value, options: {} },
    ], { x: x + 0.25, y: y + 0.95, w: 3.4, h: 1.8, fontSize: 14, paraSpaceAfter: 8 });
  });
  text(s, "Users: floor supervisors  |  Content owners: EHS, Maintenance, Quality  |  Sponsor: plant operations", { x: 0.6, y: 6.68, w: 12.1, h: 0.3, fontSize: 12, color: C.accent5 });
  s.addNotes("The business case is time and risk. Supervisors make dozens of procedural decisions per shift; today the answer lives in one of three document sets owned by different teams. The pilot targets are time to the right procedure, a full citation trail for audits, and fewer routine calls to engineers. These are targets to measure in a pilot, not results from the prototype.");
}

// ---------------------------------------------------------------- 3. solution at a glance
{
  const s = contentSlide("Context", "One question in, one cited answer out");
  const steps = [
    ["Analyze", "Detect emergency language"],
    ["Route", "LLM picks source + confidence"],
    ["Retrieve", "Parallel hybrid search per source"],
    ["Grade", "Drop weak chunks, rewrite and retry"],
    ["Generate", "Cited answer from excerpts only"],
    ["Verify", "Grounding check, regenerate once"],
  ];
  steps.forEach(([title, desc], i) => {
    const x = 0.6 + i * 2.05;
    card(s, x, 1.75, 1.85, 1.75);
    badge(s, x + 0.2, 1.95, 0.5, String(i + 1), C.accent6, 15);
    text(s, [
      { text: title, options: { bold: true, fontSize: 17, breakLine: true } },
      { text: desc, options: { fontSize: 14, color: C.accent5 } },
    ], { x: x + 0.2, y: 2.55, w: 1.5, h: 0.9 });
    if (i < steps.length - 1) arrow(s, x + 1.87, 2.62, x + 2.03, 2.62, { color: C.accent6, width: 2 });
  });

  const stats = [["3", "knowledge sources, one vector collection each"], ["13", "synthetic documents (Markdown + Word), 71 chunks"], ["11", "LangGraph nodes with bounded loops"], ["44", "unit tests, plus integration and evaluation"]];
  stats.forEach(([n, label], i) => {
    const x = 0.6 + i * 3.1;
    text(s, n, { x, y: 4.1, w: 2.8, h: 1.1, fontSize: 66, bold: true, color: C.accent1, fontFace: THEME.headFontFace });
    text(s, label, { x, y: 5.25, w: 2.6, h: 0.8, fontSize: 14, color: C.text1 });
  });
  s.addNotes("End to end, a question passes through six stages. The important design choice is that routing and retrieval are separate: the router decides where to look, hybrid search decides what to return, and two checks (grading and grounding) decide whether the system has earned the right to answer.");
}

// ---------------------------------------------------------------- 4. architecture
pres.addSection({ title: "Architecture" });
{
  const s = contentSlide("Architecture", "Layered architecture, swappable models");
  // Interfaces
  text(s, "Interfaces", { x: 0.6, y: 1.4, w: 2.4, h: 0.35, fontSize: 15, bold: true, color: C.accent5 });
  const ifaces = [["CLI", "ask / chat / ingest"], ["REST API", "FastAPI  POST /ask"], ["Streamlit UI", "supervisor demo"], ["AgentCore", "Bedrock runtime entrypoint"]];
  ifaces.forEach(([t, c], i) => node(s, 0.6, 1.85 + i * 0.85, 2.4, 0.7, t, c));
  arrow(s, 3.05, 3.3, 3.45, 3.3, { color: C.accent5 });

  // LangGraph core
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 3.5, y: 1.4, w: 5.1, h: 3.9, rectRadius: 0.1, fill: { color: C.text2 }, line: { color: C.text2 } });
  text(s, [
    { text: "PlantAssistant service", options: { bold: true, fontSize: 17, color: C.background1, breakLine: true } },
    { text: "LangGraph StateGraph, dependencies injected", options: { fontSize: 13, color: C.accent1 } },
  ], { x: 3.75, y: 1.55, w: 4.6, h: 0.75 });
  const core = [["Analyze", "guardrails"], ["Route", "structured output"], ["Retrieve x N", "Send() fan-out"], ["Grade", "relevance gate"], ["Generate", "cited answer"], ["Verify", "grounding check"]];
  core.forEach(([t, c], i) => {
    const col = i % 3, row = Math.floor(i / 3);
    node(s, 3.75 + col * 1.6, 2.5 + row * 1.25, 1.45, 1.0, t, c, { fill: C.background1 });
  });

  // Model + knowledge layers
  text(s, "Model layer  (LLM_PROVIDER)", { x: 9.0, y: 1.4, w: 3.7, h: 0.35, fontSize: 15, bold: true, color: C.accent5 });
  node(s, 9.0, 1.85, 3.7, 0.7, "Ollama  (local)", "llama3.2  +  nomic-embed-text");
  node(s, 9.0, 2.65, 3.7, 0.7, "AWS Bedrock  (production)", "Claude  +  Titan Text Embeddings v2");
  arrow(s, 8.65, 2.6, 8.95, 2.6, { color: C.accent5 });

  text(s, "Knowledge layer  (Chroma)", { x: 9.0, y: 3.55, w: 3.7, h: 0.35, fontSize: 15, bold: true, color: C.accent5 });
  [["safety_procedures", C.accent2], ["maintenance_manuals", C.accent3], ["quality_standards", C.accent4]].forEach(([t, color], i) => {
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 9.0, y: 3.95 + i * 0.45, w: 3.7, h: 0.38, rectRadius: 0.06, fill: { color }, line: { color } });
    text(s, t, { x: 9.0, y: 3.95 + i * 0.45, w: 3.7, h: 0.38, align: "center", valign: "middle", fontSize: 13, bold: true, color: C.background1, fontFace: MONO });
  });
  arrow(s, 8.65, 4.4, 8.95, 4.4, { color: C.accent5 });

  // Ingestion pipeline
  text(s, "Offline ingestion  (python -m plant_assist.ingest)", { x: 0.6, y: 5.5, w: 7, h: 0.35, fontSize: 15, bold: true, color: C.accent5 });
  const ing = [["data/docs", "md, docx, pdf"], ["Extract", "to Markdown + metadata"], ["Structure chunks", "sections, whole tables"], ["Context header", "title > section"], ["Embed + store", "1 collection / source"]];
  ing.forEach(([t, c], i) => {
    const x = 0.6 + i * 2.3;
    node(s, x, 5.95, 2.0, 0.8, t, c);
    if (i < ing.length - 1) arrow(s, x + 2.02, 6.35, x + 2.28, 6.35);
  });
  arrow(s, 10.85, 5.93, 10.85, 5.33, { color: C.accent5 });
  s.addNotes("Four thin interfaces call one service. The service is a compiled LangGraph whose nodes receive the chat model and retrievers by injection, which is why the same graph runs against Ollama on a laptop, Bedrock in AWS, or fakes in unit tests. Each knowledge source has its own Chroma collection, so routing maps directly to which index is searched. Ingestion parses YAML front matter for document IDs and revisions, splits on markdown headers and prefixes each chunk with its document title and section before embedding.");
}

// ---------------------------------------------------------------- 5. LangGraph flow
{
  const s = contentSlide("Architecture", "LangGraph flow: route, retrieve, verify");
  const W = 1.5, STEP = 1.77, Y = 1.75, H = 1.05, CY = Y + H / 2;
  const X = (i) => 0.6 + i * STEP;
  const dashed = { color: C.accent6, dash: "dash" };
  const solid = { color: C.accent5 };

  node(s, X(0), Y, W, H, "Analyze query", "input guardrails");
  node(s, X(1), Y, W, H, "Route question", "LLM + policy");
  // Retrieve fan-out stack
  text(s, "Send() fan-out", { x: X(2), y: 1.3, w: W, h: 0.3, fontSize: 11, color: C.accent6, align: "center", bold: true });
  ["safety", "maintenance", "quality"].forEach((src, i) => {
    const y = 1.62 + i * 0.47;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: X(2), y, w: W, h: 0.4, rectRadius: 0.06, fill: { color: SRC[src] }, line: { color: SRC[src] } });
    text(s, `retrieve: ${src}`, { x: X(2), y, w: W, h: 0.4, align: "center", valign: "middle", fontSize: 11, bold: true, color: C.background1 });
    arrow(s, X(1) + W, CY, X(2), y + 0.2, dashed);
    arrow(s, X(2) + W, y + 0.2, X(3), CY, solid);
  });
  node(s, X(3), Y, W, H, "Grade documents", "cosine >= 0.55");
  node(s, X(4), Y, W, H, "Generate", "cited, excerpts only");
  node(s, X(5), Y, W, H, "Verify grounding", "rules + LLM");
  node(s, X(6), Y, W, H, "Finalize", "banner + caveats", { outline: C.text1 });
  arrow(s, X(0) + W, CY, X(1), CY, solid);
  arrow(s, X(3) + W, CY, X(4), CY, dashed);
  arrow(s, X(4) + W, CY, X(5), CY, solid);
  arrow(s, X(5) + W, CY, X(6), CY, dashed);

  // Branch row
  const BY = 4.35, BH = 0.95;
  node(s, X(0), BY, W, BH, "Blocked", "unsafe / injection", { outline: C.text1 });
  arrow(s, X(0) + W / 2, Y + H, X(0) + W / 2, BY, dashed);
  node(s, X(1), BY, W, BH, "Out of scope", "polite decline", { outline: C.text1 });
  arrow(s, X(1) + W / 2, Y + H, X(1) + W / 2, BY, dashed);

  node(s, X(2), BY, W, BH, "Rewrite query", "max 1 retry", { fill: C.background2 });
  arrow(s, X(3) + 0.35, Y + H, X(2) + W - 0.25, BY, dashed);      // grade -> rewrite
  arrow(s, X(2) + 0.3, BY, X(1) + W - 0.25, Y + H, solid);         // rewrite -> route

  node(s, X(4), BY, W, BH, "No answer", "escalate to owner", { outline: C.text1 });
  arrow(s, X(3) + W - 0.3, Y + H, X(4) + 0.5, BY, dashed);          // grade -> no_answer

  // regenerate loop: verify -> generate (U shape below main row)
  const LY = 3.45;
  arrow(s, X(5) + W / 2, Y + H, X(5) + W / 2, LY, { ...dashed, head: false });
  arrow(s, X(5) + W / 2, LY, X(4) + W / 2, LY, { ...dashed, head: false });
  arrow(s, X(4) + W / 2, LY, X(4) + W / 2, Y + H, dashed);
  text(s, "regenerate with reviewer feedback\n(max 2 attempts)", { x: X(4) + W / 2 - 0.5, y: LY + 0.1, w: STEP + 1.0, h: 0.5, fontSize: 11, color: C.accent6, align: "center" });

  // Legend + takeaway
  const LG = 5.7;
  arrow(s, 0.6, LG + 0.15, 1.2, LG + 0.15, solid);
  text(s, "fixed edge", { x: 1.3, y: LG, w: 1.6, h: 0.3, fontSize: 12, color: C.accent5 });
  arrow(s, 3.0, LG + 0.15, 3.6, LG + 0.15, dashed);
  text(s, "conditional edge", { x: 3.7, y: LG, w: 2.0, h: 0.3, fontSize: 12, color: C.accent5 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 5.9, y: LG + 0.02, w: 0.5, h: 0.26, rectRadius: 0.05, fill: { color: C.background1 }, line: { color: C.text1, width: 1.5 } });
  text(s, "terminal node -> END", { x: 6.5, y: LG, w: 2.6, h: 0.3, fontSize: 12, color: C.accent5 });
  text(s, "Every loop is bounded (1 rewrite, 2 generations), so the graph always terminates with an answer, a decline or an escalation.", { x: 0.6, y: 6.2, w: 12.1, h: 0.5, fontSize: 15, color: C.text1 });
  s.addNotes("This is the compiled graph. route_question returns a list of Send objects, one per target source, so retrieval runs in parallel and results merge through a reducer on the documents channel. grade_documents decides between three exits: generate, rewrite the query and re-route (once), or escalate. After generation an LLM grounding check either finalizes or sends the answer back once with the unsupported claims as feedback. Terminal nodes are finalize, no_answer, out_of_scope and guardrail_block: unsafe requests and prompt injection are stopped in analyze_query before any LLM call.");
}

// ---------------------------------------------------------------- 5b. multi-agent?
{
  const s = contentSlide("Architecture", "Agentic workflow, not multi-agent - by design");
  const panel = (x, title, sub, color) => {
    card(s, x, 1.45, 5.9, 3.35);
    text(s, [{ text: title, options: { bold: true, fontSize: 18, color, breakLine: true } }, { text: sub, options: { fontSize: 13, color: C.accent5 } }], { x: x + 0.25, y: 1.55, w: 5.4, h: 0.75 });
  };
  // Left: what PlantAssist is
  panel(0.6, "PlantAssist today: one LangGraph workflow", "LLM at 3 decision points; everything else is deterministic code", C.accent6);
  node(s, 0.85, 2.75, 1.45, 0.8, "Router", "LLM", { fill: C.background1 });
  ["safety", "maintenance", "quality"].forEach((src, i) => {
    const y = 2.45 + i * 0.5;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 2.75, y, w: 1.45, h: 0.4, rectRadius: 0.06, fill: { color: SRC[src] }, line: { color: SRC[src] } });
    text(s, src, { x: 2.75, y, w: 1.45, h: 0.4, align: "center", valign: "middle", fontSize: 11, bold: true, color: C.background1 });
    arrow(s, 2.3, 3.15, 2.73, y + 0.2, { color: C.accent6, dash: "dash" });
    arrow(s, 4.22, y + 0.2, 4.6, 3.15, { color: C.accent5 });
  });
  node(s, 4.62, 2.75, 1.65, 0.8, "Answer + verify", "LLM x 2", { fill: C.background1 });
  text(s, "Parallel retrievers via Send() - code, not agents", { x: 0.85, y: 4.1, w: 5.4, h: 0.4, fontSize: 13, color: C.accent5 });

  // Right: multi-agent alternative
  panel(6.8, "Multi-agent alternative", "A supervisor agent delegates to domain agents with their own tools", C.accent5);
  node(s, 8.85, 2.4, 1.8, 0.7, "Supervisor", "LLM loop", { fill: C.background1 });
  [["Safety agent", C.accent2], ["Maint. agent", C.accent3], ["Quality agent", C.accent4]].forEach(([t, color], i) => {
    const x = 7.05 + i * 1.9;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 3.55, w: 1.7, h: 0.6, rectRadius: 0.06, fill: { color }, line: { color } });
    text(s, t, { x, y: 3.55, w: 1.7, h: 0.6, align: "center", valign: "middle", fontSize: 12, bold: true, color: C.background1 });
    arrow(s, 9.75, 3.1, x + 0.85, 3.53, { color: C.accent5, dash: "dash" });
  });

  const why = [
    ["Predictable and auditable", "A safety-critical answer follows the same reviewed path every time."],
    ["Cheaper and faster", "3 LLM calls per question instead of 6-12 agent turns - it matters on a CPU."],
    ["Same routing quality", "The domains are document sets, not different skills or tools."],
  ];
  why.forEach(([t, d], i) => {
    const x = 0.6 + i * 4.1;
    badge(s, x, 5.1, 0.45, String(i + 1), C.accent6, 13);
    text(s, [{ text: t, options: { bold: true, fontSize: 15, breakLine: true } }, { text: d, options: { fontSize: 14 } }], { x: x + 0.6, y: 5.0, w: 3.35, h: 1.1 });
  });
  text(s, "Go multi-agent when domains need their own tools (CMMS work orders, MES lookups, SDS database): each branch becomes a sub-agent and the router becomes the supervisor.", { x: 0.6, y: 6.25, w: 12.1, h: 0.6, fontSize: 14, color: C.accent5 });
  s.addNotes("A common question: is this multi-agent? No. It is an agentic RAG workflow: an LLM decides the route, generates and verifies, but the control flow is a fixed LangGraph with bounded loops. The parallel branches are retrievers, not autonomous agents. That was deliberate for a safety-critical, CPU-constrained prototype. The design upgrades cleanly: each retrieve branch can become a LangGraph sub-agent with its own tools, and route_question becomes the supervisor.");
}

// ---------------------------------------------------------------- 5b2. design decisions
{
  const s = contentSlide("Architecture", "Design decisions and trade-offs");
  const head = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 14 } });
  const cell = (t, o = {}) => ({ text: t, options: { fontSize: 13, color: HEX.dk1, ...o } });
  const rows = [
    ["Orchestration", "One LangGraph workflow", "Multi-agent supervisor", "Same reviewed safety path; 2-3 LLM calls"],
    ["Index layout", "One collection per source", "One collection + filter", "Routing = which index; owner isolation"],
    ["Chunking", "Structure-aware: sections, whole tables", "Fixed-size windows", "Steps and table rows stay together"],
    ["Retrieval", "Hybrid BM25 + vector (RRF)", "Vector only", "Exact part numbers, alarm codes"],
    ["Guardrails", "Rules first + LLM verifier", "LLM judge only", "Exact on numbers; works on CPU"],
    ["Models", "Ollama locally, Bedrock by config", "One provider", "Free prototype, managed production"],
    ["Vector store", "Chroma (embedded)", "OpenSearch / Bedrock KB", "Zero-ops now; swap at scale"],
  ].map(([a, b, c, d]) => [cell(a, { bold: true }), cell(b), cell(c, { color: HEX.accent5 }), cell(d)]);
  s.addTable([[head("Decision"), head("Chosen"), head("Alternative"), head("Why")], ...rows],
    { x: 0.6, y: 1.45, w: 12.1, colW: [1.9, 3.6, 2.9, 3.7], border: { type: "solid", pt: 0.75, color: "D9DEE4" }, rowH: 0.56, valign: "middle", fill: { color: HEX.lt1 } });
  text(s, "Full rationale per decision: docs/DESIGN.md", { x: 0.6, y: 6.35, w: 12.1, h: 0.35, fontSize: 12, color: C.accent5 });
  s.addNotes("Each row is a deliberate trade-off. The common thread: in a safety-critical setting, prefer deterministic, testable structure (fixed workflow, per-source indexes, structure-aware chunks, rule guardrails) and use the LLM only where judgement is needed - routing, writing, verifying.");
}

// ---------------------------------------------------------------- 5c. how routing reaches the documents
{
  const s = contentSlide("Architecture", "How a question reaches the right documents");
  const steps = [
    ["Registry", "sources.py describes each source"],
    ["LLM router", "returns RouteDecision JSON"],
    ["Policy", "plan_retrieval() adds or widens"],
    ["Dispatch", "one Send() per target source"],
    ["Search", "each retriever hits only its own collection"],
  ];
  steps.forEach(([t, d], i) => {
    const x = 0.6 + i * 2.47;
    node(s, x, 1.45, 2.2, 0.95, t, d);
    if (i < steps.length - 1) arrow(s, x + 2.22, 1.92, x + 2.45, 1.92, { color: C.accent6, width: 2 });
  });

  const head = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 14 } });
  const cell = (t, o = {}) => ({ text: t, options: { fontSize: 13, color: HEX.dk1, ...o } });
  const rows = [
    [head("Supervisor question"), head("Router decided"), head("Policy applied"), head("Collections searched")],
    [cell("Replace the HP-200 cylinder seal"), cell("maintenance, 0.95"), cell("hands-on task: + safety with LOTO/PPE query"), cell("maintenance_manuals, safety_procedures")],
    [cell("10 gallons of solvent spilled"), cell("safety, 0.99"), cell("emergency: banner + safety mandatory"), cell("safety_procedures")],
    [cell("8 points above the X-bar center line"), cell("quality, 0.90"), cell("none"), cell("quality_standards")],
    [cell("What's on the cafeteria menu?"), cell("out_of_scope, 0.95"), cell("confident decline"), cell("none - no LLM answer")],
    [cell("Any question the router is unsure of", { italic: true }), cell("confidence < 0.6", { italic: true }), cell("fan out to every source", { italic: true }), cell("all three; grading filters", { italic: true })],
  ];
  s.addTable(rows, { x: 0.6, y: 2.75, w: 12.1, colW: [3.3, 2.1, 3.6, 3.1], border: { type: "solid", pt: 0.75, color: "D9DEE4" }, rowH: 0.5, valign: "middle", fill: { color: HEX.lt1 } });
  text(s, "First four rows are actual routing decisions from the live run on llama3.2; the last row is the policy rule.", { x: 0.6, y: 6.3, w: 12.1, h: 0.35, fontSize: 12, color: C.accent5 });
  s.addNotes("Routing is two-stage. The LLM classifies the question into a typed RouteDecision using descriptions generated from the source registry. Deterministic policy then turns that decision into retrieval targets, and dispatch fans out one parallel retrieve branch per target. Because each source has its own Chroma collection, a maintenance question can never be answered from a quality document by accident.");
}

// ---------------------------------------------------------------- 6. routing
{
  const s = contentSlide("Architecture", "Routing: LLM decides, policy enforces");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.5, w: 5.7, h: 3.3, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 } });
  const code = [
    "class RouteDecision(BaseModel):",
    "    primary_source: Literal[",
    "        \"safety\", \"maintenance\",",
    "        \"quality\", \"out_of_scope\"]",
    "    secondary_sources: list[...]",
    "    confidence: float   # 0..1",
    "    rationale: str",
    "",
    "llm.with_structured_output(",
    "    RouteDecision)",
  ].join("\n");
  text(s, code, { x: 0.85, y: 1.75, w: 5.3, h: 2.9, fontFace: MONO, fontSize: 14, color: C.background1 });
  text(s, [
    { text: "Prompt is generated from the source registry, ", options: { breakLine: false } },
    { text: "so adding a source is one registry entry and a folder.", options: {} },
  ], { x: 0.6, y: 5.05, w: 5.7, h: 0.7, fontSize: 14, color: C.accent5 });
  text(s, "If the LLM fails or returns invalid JSON, a keyword router takes over - the request never crashes.", { x: 0.6, y: 5.85, w: 5.7, h: 0.7, fontSize: 14, color: C.accent5 });

  const rules = [
    ["Low confidence (< 0.6)", "Search every source; the relevance gate removes noise.", C.accent6],
    ["Confident out-of-scope", "Decline politely - no retrieval, no generated answer.", C.accent5],
    ["Emergency language", "Safety always searched; a fixed emergency banner is prepended.", C.accent2],
    ["Hands-on maintenance", "Add a LOTO/PPE-focused safety search that survives grading.", C.accent3],
  ];
  text(s, "Plant policy applied after the classifier", { x: 6.9, y: 1.45, w: 5.8, h: 0.4, fontSize: 18, bold: true, color: C.accent5 });
  rules.forEach(([title, desc, color], i) => {
    const y = 2.0 + i * 1.18;
    card(s, 6.9, y, 5.8, 1.02);
    badge(s, 7.1, y + 0.23, 0.56, String(i + 1), color, 16);
    text(s, [
      { text: title, options: { bold: true, fontSize: 16, breakLine: true } },
      { text: desc, options: { fontSize: 14, color: C.text1 } },
    ], { x: 7.85, y: y + 0.1, w: 4.7, h: 0.85, valign: "middle" });
  });
  s.addNotes("The classifier is an LLM with structured output: Ollama uses native JSON-schema decoding, Bedrock uses tool calling. Its decision is advisory. Deterministic plant policy then decides what is actually searched. Low confidence widens the search instead of guessing, and safety is added whenever the question is an emergency or describes hands-on work on equipment, because the maintenance manual alone is not a safe answer.");
}

// ---------------------------------------------------------------- 6b. extraction + chunking
{
  const s = contentSlide("Architecture", "Extraction and structure-aware chunking");
  text(s, "Extraction: every format becomes Markdown", { x: 0.6, y: 1.4, w: 5.9, h: 0.4, fontSize: 17, bold: true, color: C.accent5 });
  const formats = [
    [".md", "YAML front matter; native headings, pipe tables, lists"],
    [".docx", "Heading styles to #/##/###; tables to Markdown, in body order"],
    [".pdf", "Font-size headings; tables placed in reading order (pdfplumber)"],
  ];
  formats.forEach(([f, d], i) => {
    const y = 1.9 + i * 0.95;
    card(s, 0.6, y, 5.9, 0.8);
    text(s, f, { x: 0.8, y, w: 0.9, h: 0.8, fontFace: MONO, fontSize: 15, bold: true, valign: "middle" });
    text(s, d, { x: 1.75, y, w: 4.6, h: 0.8, fontSize: 14, valign: "middle" });
  });
  text(s, "Chunking rules", { x: 6.9, y: 1.4, w: 5.8, h: 0.4, fontSize: 17, bold: true, color: C.accent5 });
  const rules = [
    ["Never cross a section", "chunk = one heading path, cited as Title > Section"],
    ["Never split a table that fits", "bigger tables split by rows, header repeated"],
    ["Pack a section up to the size", "only oversized paragraphs are split, with overlap"],
    ["Prefix a contextual header", "so a bare table row is findable by 'HP-200 torque'"],
  ];
  rules.forEach(([t, d], i) => {
    const y = 1.9 + i * 0.72;
    badge(s, 6.9, y + 0.05, 0.45, String(i + 1), C.accent4, 13);
    text(s, [{ text: t, options: { bold: true, fontSize: 15, breakLine: true } }, { text: d, options: { fontSize: 13, color: C.accent5 } }], { x: 7.5, y, w: 5.2, h: 0.68 });
  });
  const sizes = [["900", "chars per chunk (~225 tokens)"], ["2,500", "chars: max table kept whole"], ["120", "chars overlap (long paragraphs)"], ["71", "chunks, avg 400 chars, 13 docs"]];
  sizes.forEach(([v, l], i) => {
    const x = 0.6 + i * 3.1;
    text(s, v, { x, y: 4.95, w: 2.9, h: 0.8, fontSize: 40, bold: true, color: C.accent4, fontFace: THEME.headFontFace });
    text(s, l, { x, y: 5.75, w: 2.8, h: 0.5, fontSize: 14 });
  });
  text(s, "Sizes are .env settings; the index stores a fingerprint of model + chunk settings and rebuilds itself when they change. Word and PDF versions of the same document produce identical chunks (tested).", { x: 0.6, y: 6.3, w: 12.1, h: 0.55, fontSize: 12, color: C.accent5 });
  s.addNotes("Fixed-size windows cut procedures mid-step and tables mid-row. Here every format is first normalised to Markdown, so tables survive as tables, then chunked by structure. 900 characters is roughly one procedure section; tables stay whole up to 2,500 characters and are otherwise split by rows with the header repeated. The contextual header puts the document and section into every chunk so both embeddings and BM25 can match a bare table row.");
}

// ---------------------------------------------------------------- 7. retrieval
{
  const s = contentSlide("Architecture", "Hybrid retrieval over per-source indexes");
  text(s, "Query time, per routed source", { x: 0.6, y: 1.45, w: 7.2, h: 0.4, fontSize: 18, bold: true, color: C.accent5 });
  const steps = [
    ["Vector search", "Chroma cosine similarity (nomic-embed-text or Titan v2)"],
    ["BM25 keyword search", "Exact plant vocabulary: part numbers, alarm codes, 'gland retainer'"],
    ["Reciprocal rank fusion", "Merge both rankings; keep cosine as the absolute relevance signal"],
    ["Relevance gate + interleave", "Drop chunks below 0.55; interleave sources, max 6 excerpts"],
  ];
  steps.forEach(([t, d], i) => {
    const y = 2.0 + i * 1.08;
    badge(s, 0.6, y + 0.1, 0.55, String(i + 1), C.accent6, 15);
    text(s, [
      { text: t, options: { bold: true, fontSize: 16, breakLine: true } },
      { text: d, options: { fontSize: 14, color: C.accent5 } },
    ], { x: 1.4, y, w: 6.3, h: 0.95 });
  });

  card(s, 8.2, 1.5, 4.5, 4.9);
  text(s, "Why hybrid: measured on our corpus", { x: 8.45, y: 1.7, w: 4.0, h: 0.4, fontSize: 16, bold: true });
  text(s, "Query: \"What is the torque for the gland retainer bolts?\"", { x: 8.45, y: 2.2, w: 4.0, h: 0.7, fontSize: 14, italic: true });
  text(s, "Vector only", { x: 8.45, y: 3.05, w: 4.0, h: 0.3, fontSize: 14, bold: true, color: C.accent5 });
  text(s, [{ text: "#2", options: { bold: true, fontSize: 40, color: C.accent2 } }, { text: "   behind 'Belt Tension'", options: { fontSize: 14, color: C.text1 } }], { x: 8.45, y: 3.35, w: 4.0, h: 0.8, valign: "middle" });
  text(s, "Hybrid (vector + BM25)", { x: 8.45, y: 4.3, w: 4.0, h: 0.3, fontSize: 14, bold: true, color: C.accent5 });
  text(s, [{ text: "#1", options: { bold: true, fontSize: 40, color: C.accent4 } }, { text: "   HP-200 seal procedure", options: { fontSize: 14, color: C.text1 } }], { x: 8.45, y: 4.6, w: 4.0, h: 0.8, valign: "middle" });
  text(s, "Off-topic queries score below 0.50 everywhere, so the gate also detects 'not in the docs'.", { x: 8.45, y: 5.45, w: 4.0, h: 0.85, fontSize: 13, color: C.accent5 });
  s.addNotes("Small embedding models compress similarity scores: on this corpus relevant chunks score 0.62 to 0.85 and unrelated chunks 0.48 to 0.65. BM25 fixes ranking for exact terminology, and the cosine floor of 0.55 is what lets the graph detect that a question is not covered and escalate instead of answering.");
}

// ---------------------------------------------------------------- 7b. code walkthrough
pres.addSection({ title: "Code walkthrough" });
function codeCard(slide, x, y, w, h, code, fontSize = 13) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 } });
  text(slide, code, { x: x + 0.25, y: y + 0.2, w: w - 0.5, h: h - 0.4, fontFace: MONO, fontSize, color: C.background1 });
}
{
  const s = contentSlide("Code walkthrough", "Code map: one responsibility per module");
  const groups = [
    ["Config and models", C.accent1, [["config.py", "settings from .env"], ["llm.py", "Ollama / Bedrock factories"], ["sources.py", "source registry"]]],
    ["Knowledge", C.accent4, [["loaders.py", "md, docx, pdf -> Markdown"], ["chunking.py", "sections + whole tables"], ["ingest.py", "index per source"], ["retrieval.py", "hybrid BM25 + vector"]]],
    ["Orchestration", C.accent6, [["router.py", "RouteDecision + policy"], ["guardrails.py", "input + output rules"], ["nodes.py", "11 node functions"], ["graph.py / state.py", "wiring + reducers"]]],
    ["Interfaces", C.accent3, [["service.py", "ask() for all callers"], ["cli.py / api.py", "terminal and REST"], ["streamlit_app.py", "supervisor UI"], ["agentcore_app.py", "AWS runtime"]]],
    ["Quality and ops", C.accent2, [["observability.py", "LangSmith + audit log"], ["tests/", "44 unit + 3 integration"], ["eval/", "routing, answers, guardrails"]]],
  ];
  groups.forEach(([title, color, files], i) => {
    const x = 0.6 + i * 2.47;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.45, w: 2.3, h: 0.5, rectRadius: 0.06, fill: { color }, line: { color } });
    text(s, title, { x, y: 1.45, w: 2.3, h: 0.5, align: "center", valign: "middle", fontSize: 14, bold: true, color: C.background1 });
    files.forEach(([f, d], j) => {
      const y = 2.1 + j * 1.05;
      card(s, x, y, 2.3, 0.9);
      text(s, [{ text: f, options: { bold: true, fontFace: MONO, fontSize: 13, breakLine: true } }, { text: d, options: { fontSize: 13, color: C.accent5 } }], { x: x + 0.15, y, w: 2.05, h: 0.9, valign: "middle" });
    });
  });
  text(s, "Read in this order: sources.py -> router.py -> nodes.py -> graph.py -> service.py. Everything a node needs (LLM, retrievers, settings) is injected, so tests swap in fakes.", { x: 0.6, y: 6.35, w: 12.1, h: 0.6, fontSize: 14, color: C.text1 });
  s.addNotes("The package is plant_assist. Config and model factories are the only place that knows about Ollama or Bedrock. The registry in sources.py drives the router prompt, the routing schema and the keyword fallback, so adding a fourth source is one entry plus a docs folder. nodes.py holds the node logic, graph.py only wires it, and service.py is the single entry point every interface calls.");
}
{
  const s = contentSlide("Code walkthrough", "Code: wiring the graph (graph.py)");
  codeCard(s, 0.6, 1.45, 7.3, 4.6, [
    "g = StateGraph(GraphState)",
    "g.add_node(\"route_question\", n.route_question)",
    "g.add_node(\"retrieve\", n.retrieve)          # ... 10 nodes",
    "",
    "g.add_conditional_edges(\"route_question\",",
    "    n.dispatch, [\"retrieve\", \"out_of_scope\"])",
    "g.add_edge(\"retrieve\", \"grade_documents\")",
    "g.add_conditional_edges(\"grade_documents\",",
    "    n.decide_after_grading,",
    "    [\"generate\", \"rewrite_query\", \"no_answer\"])",
    "g.add_edge(\"rewrite_query\", \"route_question\")",
    "",
    "def dispatch(state):                 # nodes.py",
    "    targets = state.get(\"targets\") or []",
    "    if not targets:",
    "        return \"out_of_scope\"",
    "    return [Send(\"retrieve\", RetrieveTask(**t))",
    "            for t in targets]",
  ].join("\n"), 13);
  const points = [
    ["Send() fan-out", "dispatch returns one Send per target source, so retrievers run in parallel in a single step."],
    ["Reducer merges results", "documents: Annotated[list, merge_documents] concatenates branch outputs; None resets it before a rewrite."],
    ["Edges are plain functions", "decide_after_grading reads state and returns a node name - unit-tested without any model."],
  ];
  points.forEach(([t, d], i) => {
    const y = 1.5 + i * 1.75;
    badge(s, 8.25, y, 0.5, String(i + 1), C.accent6, 14);
    text(s, [{ text: t, options: { bold: true, fontSize: 16, breakLine: true } }, { text: d, options: { fontSize: 14 } }], { x: 8.9, y: y - 0.05, w: 3.8, h: 1.55 });
  });
  s.addNotes("graph.py only wires nodes. The key LangGraph features are conditional edges and Send. dispatch turns the router's targets into Send objects, one per source, which LangGraph runs in parallel; the documents channel has a custom reducer so the parallel outputs merge, and returning None resets it before a corrective rewrite.");
}
{
  const s = contentSlide("Code walkthrough", "Code: routing decision and policy (router.py)");
  codeCard(s, 0.6, 1.45, 6.4, 4.85, [
    "# nodes.route_question",
    "try:",
    "    decision = llm_route(llm, query)",
    "    method = \"llm\"",
    "except Exception:",
    "    decision = keyword_route(query)",
    "    method = \"keyword-fallback\"",
    "targets = plan_retrieval(decision, query,",
    "                         safety_alert, 0.6)",
    "",
    "# router.plan_retrieval (simplified)",
    "if decision.confidence < threshold:",
    "    sources = ALL_SOURCES       # fan out",
    "elif decision.primary == OUT_OF_SCOPE:",
    "    return []                   # decline",
    "if safety_alert or hands_on_task(q):",
    "    targets.append(RetrievalTarget(",
    "        \"safety\", LOTO_PREFIX + q,",
    "        mandatory=True))",
  ].join("\n"), 13);
  const points = [
    ["Typed LLM output", "llm.with_structured_output(RouteDecision): JSON schema on Ollama, tool calling on Bedrock."],
    ["Never crashes", "Any router error falls back to keyword routing generated from the same registry."],
    ["Policy is code", "Low confidence widens the search; emergencies and hands-on work force a safety search."],
    ["Mandatory chunks", "Policy-added safety results keep their best chunk through grading, so LOTO is never dropped."],
  ];
  points.forEach(([t, d], i) => {
    const y = 1.5 + i * 1.32;
    badge(s, 7.35, y, 0.5, String(i + 1), C.accent6, 14);
    text(s, [{ text: t, options: { bold: true, fontSize: 16, breakLine: true } }, { text: d, options: { fontSize: 14 } }], { x: 8.0, y: y - 0.05, w: 4.7, h: 1.2 });
  });
  s.addNotes("The router has two layers. llm_route asks the model for a typed RouteDecision; if anything fails, keyword_route produces the same type from the registry keywords. plan_retrieval is deterministic and unit-tested: it is where plant policy lives, for example adding a lockout/tagout-focused safety search to every hands-on maintenance question.");
}

// ---------------------------------------------------------------- 8. walkthrough
pres.addSection({ title: "Behaviour" });
{
  const s = contentSlide("Behaviour", "Walkthrough: a seal replacement question");
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.45, w: 12.1, h: 0.7, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 } });
  text(s, "\"How do I replace the main cylinder seal on the HP-200 press?\"", { x: 0.85, y: 1.45, w: 11.6, h: 0.7, valign: "middle", fontSize: 20, bold: true, color: C.background1 });

  const trace = [
    ["Route", "maintenance, confidence 0.95 (LLM)", C.accent3],
    ["Policy", "hands-on task: add safety with a LOTO/PPE query", C.accent2],
    ["Retrieve", "maintenance 5 + safety 2 chunks, in parallel", C.accent6],
    ["Grade", "7 relevant, 6 in context; best cosine 0.85", C.accent6],
    ["Generate", "numbered steps, every line cited", C.accent6],
    ["Verify", "checker flagged 1 claim twice, so a caveat was added", C.accent6],
  ];
  trace.forEach(([t, d, color], i) => {
    const y = 2.45 + i * 0.68;
    badge(s, 0.6, y, 0.5, String(i + 1), color, 14);
    text(s, [{ text: t + "  ", options: { bold: true } }, { text: d, options: { color: C.text1 } }], { x: 1.25, y, w: 5.4, h: 0.5, valign: "middle", fontSize: 14 });
  });

  card(s, 7.0, 2.45, 5.7, 4.2);
  text(s, "Actual answer, llama3.2 on CPU (excerpt)", { x: 7.25, y: 2.6, w: 5.2, h: 0.35, fontSize: 14, bold: true, color: C.accent5 });
  text(s, [
    { text: "LOTO: apply per SOP-SAF-001 and verify zero energy state [4].", options: { breakLine: true } },
    { text: "1. Bleed the accumulator to 0 psi and lower the ram onto the safety blocks [1].", options: { breakLine: true } },
    { text: "6. Reinstall the gland and torque the retainer bolts to 210 ft-lb in a star pattern [1].", options: { breakLine: true } },
    { text: "7. Cycle the press 10 times at low pressure (500 psi) and inspect for leaks [1].", options: {} },
  ], { x: 7.25, y: 3.0, w: 5.2, h: 2.6, fontSize: 14, paraSpaceAfter: 6 });
  text(s, "[1] MM-HP-200 rev 4 > Replacing the Main Cylinder Seal Kit\n[4] SOP-SAF-001 rev D > Energy Isolation Steps", { x: 7.25, y: 5.8, w: 5.2, h: 0.65, fontSize: 12, color: C.accent5 });
  s.addNotes("A question that a supervisor would phrase as a maintenance question. The router correctly says maintenance; the policy layer adds a lockout/tagout search because the question describes hands-on work. The answer leads with the safety prerequisites and every step is cited to a document, revision and section.");
}

// ---------------------------------------------------------------- 9. guardrails
{
  const s = contentSlide("Behaviour", "Guardrails: layered, deterministic first");
  const layers = [
    ["Input", C.accent2, ["Prompt injection blocked", "Requests to defeat a protection blocked - reports allowed", "Emails and phone numbers redacted", "Length limit"]],
    ["Routing + retrieval", C.accent6, ["Confident off-topic declined", "Hands-on work adds LOTO / PPE", "Relevance gate 0.55; rewrite once, then escalate"]],
    ["Output", C.accent3, ["Citations validated", "Every number must appear in the excerpts", "Unsafe advice withheld", "LLM verifier (optional)"]],
    ["Response", C.accent1, ["Fixed emergency banner", "Caveat if still unverified", "Owner extension on escalation", "Bedrock Guardrails on AWS"]],
  ];
  layers.forEach(([title, color, items], i) => {
    const x = 0.6 + i * 3.08;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 1.45, w: 2.9, h: 0.5, rectRadius: 0.06, fill: { color }, line: { color } });
    text(s, title, { x, y: 1.45, w: 2.9, h: 0.5, align: "center", valign: "middle", fontSize: 15, bold: true, color: C.background1 });
    card(s, x, 2.05, 2.9, 2.65);
    text(s, items.map((t, j) => ({ text: t, options: { bullet: true, breakLine: j < items.length - 1 } })), { x: x + 0.15, y: 2.2, w: 2.65, h: 2.4, fontSize: 14, paraSpaceAfter: 6 });
    if (i < layers.length - 1) arrow(s, x + 2.92, 1.7, x + 3.06, 1.7, { color: C.accent5 });
  });
  const stats = [["16 / 16", "guardrail eval cases correct (block precision 1.0, recall 1.0)", C.accent4], ["13 ms", "to refuse an unsafe request - no LLM or retrieval call", C.accent2], ["Exact", "number check: an invented torque or pressure triggers regeneration, then a visible caveat", C.accent3]];
  stats.forEach(([v, l, color], i) => {
    const x = 0.6 + i * 4.1;
    text(s, v, { x, y: 4.95, w: 3.9, h: 0.75, fontSize: 36, bold: true, color, fontFace: THEME.headFontFace });
    text(s, l, { x, y: 5.7, w: 3.8, h: 0.8, fontSize: 14 });
  });
  s.addNotes("Guardrails are layered and deterministic first, so they work even when the small local model's verifier is switched off. The unsafe-request rule blocks how-to requests for defeating light curtains, interlocks or lockout, but deliberately allows reports such as 'the interlock was bypassed by night shift, what do I do?'. The numeric rule is exact for the facts that matter most on the floor: torques, pressures, limits and extensions. In AWS, Bedrock Guardrails add managed content filters and PII masking on every Claude call.");
}

// ---------------------------------------------------------------- 10. evaluation
{
  let summary = null;
  try { summary = JSON.parse(fs.readFileSync(EVAL, "utf8")).summary; } catch { /* eval not run yet */ }
  const llmEval = summary && (summary.mode === "llm" || summary.mode === "full");
  const s = contentSlide("Behaviour", llmEval ? "LLM routing on the labelled question set" : "Live run: four questions, four right routes");
  const pct = (v) => (v == null ? "n/a" : `${Math.round(v * 100)}%`);

  if (llmEval) {
    const order = ["safety", "maintenance", "quality", "out_of_scope"];
    const labels = ["Safety", "Maintenance", "Quality", "Out of scope"];
    const results = JSON.parse(fs.readFileSync(EVAL, "utf8")).results;
    const kwAcc = order.map((src) => {
      const rows = results.filter((r) => r.expected_source === src);
      return rows.length ? Math.round((rows.filter((r) => r.keyword_route === src).length / rows.length) * 100) : 0;
    });
    const llmAcc = order.map((src) => Math.round((summary.per_source_accuracy[src] || 0) * 100));
    s.addChart(pres.charts.BAR, [
      { name: "LLM router", labels, values: llmAcc },
      { name: "Keyword fallback", labels, values: kwAcc },
    ], {
      x: 0.6, y: 1.45, w: 7.4, h: 5.2, barDir: "col", barGrouping: "clustered",
      chartColors: [HEX.accent6, HEX.accent5],
      showTitle: true, title: "Routing accuracy by expected source (%)", titleFontSize: 14, titleColor: HEX.dk1, titleFontFace: "+mn-lt",
      showValue: true, dataLabelPosition: "outEnd", dataLabelFontSize: 12, dataLabelColor: HEX.dk1, dataLabelFontFace: "+mn-lt", dataLabelFormatCode: "0",
      valAxisMaxVal: 100, valAxisMinVal: 0, valAxisLabelColor: HEX.accent5, valAxisLabelFontSize: 12, valAxisLabelFontFace: "+mn-lt",
      catAxisLabelColor: HEX.dk1, catAxisLabelFontSize: 12, catAxisLabelFontFace: "+mn-lt",
      valGridLine: { color: "D9DEE4", size: 0.5 }, catGridLine: { style: "none" },
      showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: HEX.dk1, legendFontFace: "+mn-lt",
    });
    const stats = [
      [pct(summary.routing_accuracy), `LLM routing accuracy (${summary.questions} questions)`, C.accent6],
      [pct(summary.retrieval_hit_rate), "expected document retrieved (in-scope questions)", C.accent4],
      [`${(summary.avg_route_ms / 1000).toFixed(1)}s`, `avg routing latency, ${summary.model} on CPU`, C.accent1],
    ];
    stats.forEach(([n, label, color], i) => {
      const y = 1.5 + i * 1.75;
      text(s, n, { x: 8.5, y, w: 4.2, h: 0.95, fontSize: 54, bold: true, color, fontFace: THEME.headFontFace });
      text(s, label, { x: 8.5, y: y + 0.95, w: 4.2, h: 0.6, fontSize: 14 });
    });
  } else {
    const head = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 14 } });
    const cell = (t, o = {}) => ({ text: t, options: { fontSize: 14, color: HEX.dk1, ...o } });
    s.addTable([
      [head("Question"), head("Routed to"), head("Outcome"), head("Time, CPU")],
      [cell("Replace the HP-200 cylinder seal"), cell("maintenance + safety (policy)"), cell("Answered; LOTO first, 210 ft-lb torque cited"), cell("243 s")],
      [cell("10 gallons of solvent spilled"), cell("safety (emergency)"), cell("Banner + major-spill steps, ext. 5555"), cell("150 s")],
      [cell("8 points above the X-bar center line"), cell("quality"), cell("Correct verdict, thin explanation"), cell("132 s")],
      [cell("What's on the cafeteria menu?"), cell("out of scope"), cell("Declined before retrieval"), cell("< 10 s")],
    ], { x: 0.6, y: 1.45, w: 12.1, colW: [3.6, 2.9, 4.4, 1.2], border: { type: "solid", pt: 0.75, color: "D9DEE4" }, rowH: 0.5, valign: "middle", fill: { color: HEX.lt1 } });
    const stats = [
      ["4 / 4", "questions routed to the right source", C.accent4],
      ["4 / 4", "answers flagged by the 3B grounding checker - too strict; off locally, on with Claude", C.accent2],
      ["50%", "CPU cap on Ollama (OLLAMA_NUM_THREAD=2); model memory freed 60 s after use", C.accent1],
    ];
    stats.forEach(([n, label, color], i) => {
      const x = 0.6 + i * 4.1;
      text(s, n, { x, y: 4.45, w: 3.9, h: 0.9, fontSize: 48, bold: true, color, fontFace: THEME.headFontFace });
      text(s, label, { x, y: 5.35, w: 3.7, h: 0.9, fontSize: 14 });
    });
  }
  text(s, llmEval
    ? "Dataset: eval/routing_dataset.jsonl - single-domain, cross-domain and off-topic questions with expected source and document."
    : "Live run on llama3.2 (3B) on a 4-core CPU with grounding check on (before the guardrail and chunking upgrades).",
    { x: 0.6, y: 6.6, w: 12.1, h: 0.3, fontSize: 11, color: C.accent5 });
  s.addNotes(llmEval
    ? "Numbers come from eval/run_eval.py on the labelled question set, using the local 3B model on CPU. The keyword router is the safety net, not the primary path. Retrieval hit rate checks that the expected document is among the retrieved chunks for the sources the router chose."
    : "These are the four live questions run end to end on the laptop. Routing was right every time, including the policy-added safety search. The weak spot is the small local model: answers are slow on CPU and its grounding checker flags almost everything, so locally it is switched off and the CPU is capped. With Claude on Bedrock both problems go away.");
}

// ---------------------------------------------------------------- 10b. evaluation metrics
{
  let summary = null;
  try { summary = JSON.parse(fs.readFileSync(EVAL, "utf8")).summary; } catch { /* not run */ }
  const pct = (v) => (v == null ? "run eval" : `${Math.round(v * 100)}%`);
  const s = contentSlide("Behaviour", "Evaluation: what we measure and current results");
  const head = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 14 } });
  const cell = (t, o = {}) => ({ text: t, options: { fontSize: 13, color: HEX.dk1, ...o } });
  const g = summary ? summary.guardrails : null;
  const rows = [
    ["Retrieval", "Hit@5: expected document retrieved", summary ? `${pct(summary.retrieval_hit_rate)} (26 in-scope)` : "run eval"],
    ["Retrieval", "MRR: 1 / rank of first expected document", summary ? String(summary.mrr) : "run eval"],
    ["Guardrails", "Block precision / recall (16 cases)", g ? `${g.block_precision.toFixed(1)} / ${g.block_recall.toFixed(1)}` : "run eval"],
    ["Routing", "Keyword fallback accuracy (28 questions)", summary ? pct(summary.keyword_router_accuracy) : "run eval"],
    ["Routing", "LLM router accuracy", "4 / 4 live; full set: run_eval"],
    ["Answers", "Fact recall, expected doc cited, numeric grounding, latency p50/p95", "run_eval --full / LangSmith"],
  ].map(([a, b, c]) => [cell(a, { bold: true }), cell(b), cell(c, { bold: true })]);
  s.addTable([[head("Area"), head("Metric"), head("Current")], ...rows],
    { x: 0.6, y: 1.45, w: 7.6, colW: [1.4, 3.9, 2.3], border: { type: "solid", pt: 0.75, color: "D9DEE4" }, rowH: 0.55, valign: "middle", fill: { color: HEX.lt1 } });
  codeCard(s, 8.5, 1.45, 4.2, 3.4, [
    "# no chat-model calls, ~20 s",
    "python -m eval.run_eval --no-llm",
    "",
    "# + LLM router accuracy",
    "python -m eval.run_eval",
    "",
    "# + end-to-end answers",
    "python -m eval.run_eval --full",
    "",
    "# LangSmith experiment",
    "python -m eval.langsmith_eval",
  ].join("\n"), 12);
  text(s, "Keyword fallback misses still retrieve the right document: low confidence widens the search to every source. Run --no-llm in CI as a fast regression gate; run --full before changing models, prompts or thresholds.", { x: 0.6, y: 5.55, w: 12.1, h: 0.9, fontSize: 14 });
  s.addNotes("Two labelled sets: 28 questions with expected source, acceptable documents and key facts (including table-only facts), and 16 guardrail cases. The cheap mode needs only embeddings and runs in about 20 seconds, so it can gate every change. The full mode and the LangSmith experiment score answers end to end.");
}

// ---------------------------------------------------------------- 10c. monitoring
{
  const s = contentSlide("Behaviour", "Monitoring: LangSmith traces, feedback, audit log");
  const items = [
    ["Tracing", "Every node, router output, retriever call, prompt, tokens and latency - automatic once LANGSMITH_TRACING=true."],
    ["Run metadata", "Tags for provider and channel (api, streamlit, cli, eval); a run_id per question is returned to the client."],
    ["Feedback", "Helpful / Not helpful in the UI or POST /feedback becomes supervisor_rating on the run."],
    ["Experiments", "eval/langsmith_eval.py scores route, cited document, fact recall and numeric grounding."],
    ["Privacy", "PII redacted first; LANGSMITH_HIDE_INPUTS / HIDE_OUTPUTS keep document text out."],
  ];
  items.forEach(([t, d], i) => {
    const y = 1.45 + i * 0.98;
    badge(s, 0.6, y + 0.05, 0.5, String(i + 1), C.accent6, 14);
    text(s, [{ text: t, options: { bold: true, fontSize: 15, breakLine: true } }, { text: d, options: { fontSize: 13 } }], { x: 1.25, y, w: 5.6, h: 0.92 });
  });
  text(s, "Local audit log - logs/audit.jsonl (one line per question)", { x: 7.2, y: 1.4, w: 5.5, h: 0.4, fontSize: 15, bold: true, color: C.accent5 });
  codeCard(s, 7.2, 1.85, 5.5, 2.75, [
    "{\"run_id\": \"19e6c7e0-...\",",
    " \"question\": \"How do I bypass the",
    "   light curtain on the HP-200?\",",
    " \"outcome\": \"blocked\",",
    " \"guardrail\": {\"input_category\":",
    "   \"unsafe_request\"},",
    " \"cited_docs\": [],",
    " \"latency_ms\": 13}",
  ].join("\n"), 12);
  text(s, "Alert on: p95 latency, rate of no_answer / blocked / unverified answers, negative feedback per source, router fallback rate.", { x: 7.2, y: 4.85, w: 5.5, h: 0.9, fontSize: 13, color: C.text1 });
  s.addNotes("LangSmith gives full traces of each graph run with no extra code beyond configuration; the service adds a run_id, tags and metadata, and posts supervisor feedback to the run. The JSONL audit log is the plant's own offline record of every answer, which matters for safety audits regardless of any SaaS. The line shown is a real record from the prototype.");
}

// ---------------------------------------------------------------- 11a. tech stack
pres.addSection({ title: "Deployment" });
{
  const s = contentSlide("Deployment", "Tech stack");
  const head = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 14 } });
  const cell = (t, o = {}) => ({ text: t, options: { fontSize: 13, color: HEX.dk1, ...o } });
  const rows = [
    ["Orchestration", "LangGraph 1.2, LangChain core 1.6", "State machine: conditional edges, parallel Send(), reducers"],
    ["Models (local)", "Ollama 0.40: llama3.2 3B, nomic-embed-text", "Free, private, runs on a laptop CPU"],
    ["Models (AWS)", "Bedrock: Claude, Titan Embeddings v2, Guardrails", "Managed; data stays in the AWS account"],
    ["Retrieval", "Chroma 1.5 + in-process BM25", "Embedded vector store; exact-term matching"],
    ["Extraction", "PyYAML, python-docx 1.2, pdfplumber 0.11", "Front matter, Word structure, PDF tables"],
    ["Serving", "FastAPI 0.143, Streamlit 1.65, AgentCore 1.24", "REST, supervisor UI, managed agent runtime"],
    ["Monitoring", "LangSmith 0.14 + JSONL audit log", "Traces, feedback, experiments; offline record"],
    ["Quality", "pytest 9 (44 unit tests), ruff", "Fake LLM + retrievers: no model needed"],
    ["Language / config", "Python 3.12, pydantic-settings, .env", "Typed settings; provider switch by config"],
  ].map(([a, b, c]) => [cell(a, { bold: true }), cell(b), cell(c, { color: HEX.accent5 })]);
  s.addTable([[head("Layer"), head("Technology"), head("Why")], ...rows],
    { x: 0.6, y: 1.45, w: 12.1, colW: [2.1, 4.9, 5.1], border: { type: "solid", pt: 0.75, color: "D9DEE4" }, rowH: 0.5, valign: "middle", fill: { color: HEX.lt1 } });
  s.addNotes("Everything is open source or AWS-managed. The only change between the laptop and AWS is the model provider and, at scale, the vector store.");
}

// ---------------------------------------------------------------- 11. deployment
{
  const s = contentSlide("Deployment", "From laptop to AWS Bedrock by config");
  const head = (t) => ({ text: t, options: { bold: true, color: HEX.lt1, fill: { color: HEX.dk2 }, fontSize: 14 } });
  const cell = (t, o = {}) => ({ text: t, options: { fontSize: 14, color: HEX.dk1, ...o } });
  const rows = [
    [head("Layer"), head("Local prototype"), head("AWS production path")],
    [cell("Chat model", { bold: true }), cell("Ollama llama3.2 (3B, CPU)"), cell("Claude on Amazon Bedrock (ChatBedrockConverse)")],
    [cell("Embeddings", { bold: true }), cell("nomic-embed-text"), cell("Amazon Titan Text Embeddings v2")],
    [cell("Vector store", { bold: true }), cell("Chroma on disk"), cell("Chroma in container (pilot) -> OpenSearch Serverless or Bedrock Knowledge Bases")],
    [cell("Runtime", { bold: true }), cell("CLI, FastAPI, Streamlit"), cell("Bedrock AgentCore Runtime, or ECS Fargate / App Runner")],
    [cell("Ops", { bold: true }), cell("Graph trace in every response"), cell("IAM role, CloudWatch logs, LangSmith tracing, Bedrock Guardrails")],
  ];
  s.addTable(rows, { x: 0.6, y: 1.45, w: 12.1, colW: [2.0, 3.6, 6.5], border: { type: "solid", pt: 0.75, color: "D9DEE4" }, rowH: 0.55, valign: "middle", fill: { color: HEX.lt1 } });

  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 5.15, w: 12.1, h: 1.35, rectRadius: 0.08, fill: { color: C.text2 }, line: { color: C.text2 } });
  text(s, "The switch is environment only - no code changes:", { x: 0.85, y: 5.27, w: 11.6, h: 0.35, fontSize: 14, bold: true, color: C.accent1 });
  text(s, "LLM_PROVIDER=bedrock   EMBEDDING_PROVIDER=bedrock   AWS_REGION=us-east-1\nBEDROCK_MODEL_ID=<Claude model or inference-profile ID>   ->   index rebuilds automatically", { x: 0.85, y: 5.67, w: 11.6, h: 0.85, fontSize: 14, color: C.background1, fontFace: MONO });
  s.addNotes("The model factory chooses Ollama or Bedrock from environment variables. The index records which embedding model built it, so switching to Titan triggers an automatic rebuild instead of a dimension-mismatch error. For a pilot, the container builds its small Chroma index at start-up; for production the vector store moves to a managed service. The README has step-by-step AgentCore and App Runner instructions.");
}

// ---------------------------------------------------------------- 12. next steps
{
  const s = pres.addSlide({ masterName: "CLOSING_DARK", sectionTitle: "Deployment" });
  s.addText("Next steps", { placeholder: "title" });
  s.addText("From prototype to a one-line pilot", { placeholder: "subtitle" });
  const steps = [
    "Pilot on one production line with real SOPs synced from the document management system",
    "Move retrieval to OpenSearch Serverless or Bedrock Knowledge Bases with revision-aware sync",
    "Multi-turn follow-ups (LangGraph checkpointer); domain sub-agents with CMMS / MES tools",
    "Supervisor thumbs-up/down feeding LangSmith evaluations in CI",
    "SSO, role-based document access and Bedrock Guardrails",
  ];
  steps.forEach((t, i) => {
    const y = 3.0 + i * 0.82;
    badge(s, 0.8, y, 0.55, String(i + 1), C.accent1, 16);
    text(s, t, { x: 1.6, y, w: 10.9, h: 0.55, fontSize: 18, color: C.background1, valign: "middle" });
  });
  s.addNotes("The architecture is ready for a pilot. The highest-value next step is connecting real, revision-controlled documents and putting the assistant in front of a few supervisors to collect feedback, which then becomes the evaluation set.");
}

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log(`Wrote ${OUT}`);
})();
