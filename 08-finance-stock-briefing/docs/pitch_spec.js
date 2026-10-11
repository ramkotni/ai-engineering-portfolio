// One-slide client pitch.   cd tools/deck && node pitch.js ../../08-finance-stock-briefing
const fs = require("fs");
const path = require("path");

const quotes = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "data", "raw", "quotes.json"), "utf8"));
const nwrb = quotes.NWRB.weekly_closes;

module.exports = {
  fileName: "Stock_Briefing_Pitch.pptx",
  accent: "2D7DD2",
  title: "Up to Speed on Any Stock in Minutes",
  tagline: "Quote, key financials and a cited summary of the latest SEC filings - ready before the client call",
  client: "Wealth management firm\nPrototype - live or synthetic data",
  problem: [
    "Before a client call an advisor needs the price, the trend and the risks - buried in a 100-page 10-K, a 10-Q and recent 8-Ks.",
    "Few advisors have the time to read them, so preparation is uneven.",
    "Anything said to a client must stay factual - no unsanctioned recommendations.",
  ],
  users: [
    "Financial advisors and research analysts",
    "Compliance officers (review + audit trail)",
    "Client-service associates (quote look-ups only)",
  ],
  steps: [
    ["Resolve the company", "Ticker or name, any US issuer via the SEC list"],
    ["Three agents in parallel", "Quote (market data) | financials (XBRL) | filings (RAG)"],
    ["Read the filings properly", "10-K / 10-Q / 8-K HTML to Item sections; TOC and page noise removed"],
    ["Numbers computed in code", "Growth, margins, P/E, 52-week position - never by the LLM"],
    ["Write, then compliance review", "Cited bullets; recommendation language removed; data timestamps"],
  ],
  highlightStep: 2,
  chart: {
    name: "NWRB", title: "NWRB weekly close - 52 weeks (synthetic demo company)",
    labels: nwrb.map((w) => w.date), values: nwrb.map((w) => w.close),
    min: Math.floor(Math.min(...nwrb.map((w) => w.close)) / 5) * 5 - 5, max: Math.ceil(Math.max(...nwrb.map((w) => w.close)) / 5) * 5 + 5,
  },
  proof: [
    ["6 / 6", "filings parsed into the right sections (also tested on a real 8.5 MB 10-K)"],
    ["100%", "of 10 test questions found the right filing passage; 0 cross-company mix-ups"],
    ["5 / 5", "advice statements removed by the compliance filter; 4 / 4 facts kept"],
    ["+0.05", "retrieval F1 after a RAGAS-driven tuning of the search (0.934 to 0.986)"],
  ],
  trust: [
    "No buy / sell / hold, price targets or MNPI",
    "Every figure from a filing or a data feed, with its timestamp",
    "Role-based access; audit log for compliance",
    "LangSmith tracing, metrics, evaluation suite",
  ],
  value: "Preparation per stock from ~30-60 minutes to a few, consistent coverage of risks and events, and supervised, traceable output.",
  next: "20-advisor pilot: licensed quotes, firm research notes, Claude on Amazon Bedrock; measure prep time and compliance edits.",
  notes: "Demo: brief NWRB as financial_advisor (snapshot, financials, cited bullets); show the compliance-removed statement list; ask 'Should my "
    + "client buy HLXB?' (refused); quote-only as client_service_associate; live mode: brief MSFT (real 10-K parsed from EDGAR). Trade-offs: "
    + "Yahoo chart API is unofficial (swap for a licensed feed), live mode indexes the first 15k characters per section on CPU, 3B model is slow.",
};
