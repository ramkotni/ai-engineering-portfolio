// One-slide client pitch.   cd tools/deck && node pitch.js ../../07-healthcare-condition-briefing
const path = require("path");

module.exports = {
  fileName: "Condition_Briefing_Pitch.pptx",
  accent: "2D9C8F",
  title: "Condition Briefings in Minutes, Not Days",
  tagline: "An AI analyst that turns guidelines, pipelines and internal plans into a cited, structured briefing",
  client: "Health system strategy team\nPrototype on synthetic data",
  problem: [
    "Every condition review takes days: guideline PDFs, pipeline registries and internal plans are read by hand.",
    "The facts that matter hide in two-column PDFs, multi-page tables and figures that search tools cannot read.",
    "Numbers are re-typed and pipelines go stale; briefings look different every time.",
  ],
  users: [
    "Strategy analysts and service-line directors",
    "Executives (short executive briefing)",
    "Physician advisor; external consultants see public sources only",
  ],
  steps: [
    ["Read complex documents", "Two-column PDFs, page-spanning tables, captioned figures"],
    ["Index with citations", "Every chunk keeps its document, section and access level"],
    ["Four agents in parallel", "Standard of care | pipeline | key players | internal strategy"],
    ["Counts computed in code", "Trials, phases and rankings from the registry, live from ClinicalTrials.gov"],
    ["One writer, then checks", "Numbers and IDs verified against sources; patient advice refused"],
  ],
  highlightStep: 0,
  image: {
    path: path.join(__dirname, "..", "data", "extracted", "images", "CARD-GL-2026_p2_img1.png"),
    ratio: 1200 / 820, h: 1.55,
    caption: "Extracted from page 2 of the guideline PDF and made searchable: 'When is CRT-D indicated?' is answered from this figure.",
  },
  proof: [
    ["8 / 8", "PDF extraction checks: headers, columns, merged table, figures, footnotes"],
    ["100%", "of 12 test questions found the right source (tables, figures, footnotes)"],
    ["0", "internal documents shown to the external-consultant role"],
    ["100%", "guardrail precision and recall (14 cases)"],
  ],
  trust: [
    "Every bullet cites a numbered source",
    "Counts and rankings computed, not generated",
    "Vision misreads flagged (caught 'Hydralazine' read as 'Hydrochlorothiazide')",
    "Role-based access, PHI redaction, audit log, LangSmith tracing",
  ],
  value: "Briefing prep from days to minutes, one consistent format, and pipeline views that refresh from ClinicalTrials.gov on demand.",
  next: "4-week pilot: 3 service lines, your guideline library, Claude on Amazon Bedrock; measure prep time and analyst edits.",
  notes: "Demo: generate the HFrEF briefing as strategy_analyst, then as external_consultant (no internal section); open the Extraction tab to show "
    + "headers removed, the merged table and the figures; ask 'When is CRT-D indicated?' to show an answer that only exists in an image; "
    + "toggle live data and brief 'atrial fibrillation' from ClinicalTrials.gov. Trade-offs: CPU-only 3B model is slow (minutes); Bedrock fixes "
    + "latency. Vision captions can misread - flagged, not silently trusted.",
};
