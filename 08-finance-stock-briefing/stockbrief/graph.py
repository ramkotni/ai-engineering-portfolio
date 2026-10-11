r"""Stock-briefing workflow (LangGraph): three data agents run in parallel, then one writer call and a compliance review.

  START -> guard_input --blocked--> finish
           resolve_company (ticker or name; synthetic catalogue or SEC ticker list)
           -> authorize (task, live-data permission) --denied / unknown--> finish
           task = quote    -> quote_agent -> render_quote -> END
           task = qa       -> prepare_filings -> retrieve -> answer -> verify -> END
           task = briefing -> prepare_filings -> [quote_agent | financials_agent | filings_agent]   (parallel)
                           -> write_briefing (one LLM call, numbered evidence) -> compliance_review -> END

The quote, price metrics and financial ratios are computed in code (stockbrief.market / stockbrief.financials);
the LLM summarises the filing text and cites the computed figures. The compliance review removes any
recommendation language and checks every number against the evidence.
"""

import logging
import operator
import re
from datetime import date
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel

from stockbrief import rbac
from stockbrief.companies import Company, resolve
from stockbrief.config import Settings, get_settings
from stockbrief.financials import get_financials, metrics
from stockbrief.guardrails import DISCLAIMER, check_answer, check_input, compliance_review
from stockbrief.market import get_quote, price_metrics
from stockbrief.prompts import SECTIONS, STYLES, get_template

log = logging.getLogger(__name__)
MAX_BULLETS = 6                 # small models ignore "2-4 bullets"; the structure is enforced in code
SECTION_QUERIES = {   # briefing section -> (filing section group, retrieval query)
    "business": ("business", "business overview products segments customers revenue mix employees"),
    "mdna": ("mdna", "revenue growth margin drivers results outlook liquidity cash"),
    "risks": ("risks", "most significant risks uncertainties competition regulation supply"),
    "events": ("events", "material agreement results announcement outlook update"),
}


def _merge(a: dict, b: dict) -> dict:
    return {**a, **b}


class State(TypedDict, total=False):
    request: str
    role: str
    task: str                       # briefing | qa | quote
    source: str                     # synthetic | live
    company: dict
    blocked: bool
    guardrail: dict
    data: Annotated[dict, _merge]   # outputs of the parallel agents
    hits: list[dict]
    context: list[dict]
    evidence: list[dict]
    briefing: dict
    answer: str
    citations: list[dict]
    outcome: str
    notes: list[str]
    trace: Annotated[list[str], operator.add]


def build_graph(llm: BaseChatModel | None = None, retrievers: dict | None = None, settings: Settings | None = None,
                quote_fn=None, financials_fn=None, prepare_fn=None):
    from langgraph.graph import END, START, StateGraph

    s = settings or get_settings()
    if llm is None:
        from stockbrief.llm import get_chat_model

        llm = get_chat_model()
    if retrievers is None:
        from stockbrief.retrieval import get_retrievers

        retrievers = get_retrievers()
    store = retrievers["filings"]
    quote_fn = quote_fn or (lambda c, src: get_quote(c.ticker, src, s))
    financials_fn = financials_fn or (lambda c, src: get_financials(c.ticker, src, c.cik, s))

    def _default_prepare(c: Company, src: str) -> str:
        if src != "live":
            return "synthetic filings (pre-indexed)"
        from stockbrief.ingest import ensure_live_ticker

        info = ensure_live_ticker(c)
        return f"SEC EDGAR: {', '.join(f['form'] + ' ' + f['filed'] for f in info['filings'])}" + (" (cached)" if info["cached"] else "")

    prepare = prepare_fn or _default_prepare

    def _company(state: State) -> Company:
        return Company(**state["company"])

    def _llm(messages, fallback: str) -> tuple[str, bool]:
        try:
            text = str(llm.invoke(messages).content).strip()
            return (text, True) if text else (fallback, False)
        except Exception as exc:  # noqa: BLE001 - degrade to extractive, never crash
            log.warning("LLM failed; extractive fallback: %s", exc)
            return fallback, False

    # ------------------------------------------------------------ front end
    def guard_input(state: State) -> dict:
        chk = check_input(state["request"], s.max_question_chars)
        return {"request": chk.text, "blocked": not chk.allowed, "answer": chk.message or "", "notes": [], "data": {},
                "guardrail": {"input_category": chk.category, "input_flags": chk.flags}, "trace": [f"guard_input: {chk.category or 'pass'}"]}

    def resolve_company(state: State) -> dict:
        role = rbac.get_role(state["role"])
        source = state.get("source", s.data_source)
        notes = list(state.get("notes", []))
        if source == "live" and not role.live_data:
            source = "synthetic"
            notes.append(f"Live market data is not enabled for the {role.name} role; the synthetic demo data was used.")
        try:
            c = resolve(state["request"], source, s)
        except Exception as exc:  # noqa: BLE001 - e.g. SEC_USER_AGENT not configured or network down
            return {"outcome": "unavailable", "answer": f"Live data is unavailable: {exc}", "trace": [f"resolve_company: error {type(exc).__name__}"]}
        return {"company": c.__dict__ if c else {}, "source": source, "notes": notes,
                "trace": [f"resolve_company: {c.ticker if c else 'none'} ({source})"]}

    def authorize(state: State) -> dict:
        if state.get("outcome"):
            return {}
        role = rbac.get_role(state["role"])
        task = state.get("task", "briefing")
        if not role.allows(task):
            return {"outcome": "denied", "answer": f"Your role ({role.name}) cannot use '{task}'. Allowed: {', '.join(role.tasks)}.",
                    "trace": ["authorize: DENIED task"]}
        if not state.get("company"):
            hint = "NWRB or HLXB (synthetic demo companies)" if state["source"] != "live" else "a listed US ticker"
            return {"outcome": "unknown_company", "answer": f"I couldn't identify the company. Try a ticker such as {hint}.",
                    "trace": ["authorize: unknown company"]}
        return {"trace": [f"authorize: {role.name} task={task}"]}

    # ------------------------------------------------------------ agents
    def prepare_filings(state: State) -> dict:
        try:
            info = prepare(_company(state), state["source"])
        except Exception as exc:  # noqa: BLE001
            return {"notes": state["notes"] + [f"Filings unavailable ({type(exc).__name__}); briefing uses market data only."],
                    "trace": [f"prepare_filings: error {type(exc).__name__}"]}
        return {"trace": [f"prepare_filings: {info}"]}

    def quote_agent(state: State) -> dict:
        try:
            q = quote_fn(_company(state), state["source"])
        except Exception as exc:  # noqa: BLE001
            return {"data": {"quote": None, "quote_error": type(exc).__name__}, "trace": [f"quote_agent: error {type(exc).__name__}"]}
        return {"data": {"quote": q}, "trace": [f"quote_agent: {q['price'] if q else 'no quote'} ({q['source'] if q else '-'})"]}

    def financials_agent(state: State) -> dict:
        try:
            fin = financials_fn(_company(state), state["source"])
        except Exception as exc:  # noqa: BLE001
            return {"data": {"financials": None}, "trace": [f"financials_agent: error {type(exc).__name__}"]}
        m = metrics(fin) if fin and fin.get("annual") else None
        return {"data": {"financials": fin, "metrics": m}, "trace": [f"financials_agent: FY{m['fiscal_year'] if m else '-'}"]}

    def filings_agent(state: State) -> dict:
        ticker = _company(state).ticker
        found = {}
        for key, (group, query) in SECTION_QUERIES.items():
            k = 2 if key == "events" else s.section_k
            found[key] = store.search(query, k, {"ticker": ticker, "group": group})
        return {"data": {"filings": found}, "trace": [(f"filings_agent: {sum(map(len, found.values()))} chunks "
                                                      f"{ {k: len(v) for k, v in found.items()} }")]}

    def write_briefing(state: State) -> dict:
        role, c, d = rbac.get_role(state["role"]), _company(state), state["data"]
        q, fin_m = d.get("quote"), d.get("metrics")
        pm = price_metrics(q, fin_m.get("eps_diluted") if fin_m else None,
                           (d.get("financials") or {}).get("shares_outstanding_m")) if q else None
        evidence = []
        if q:
            evidence.append({"id": "MARKET", "content": "Market snapshot (computed in code): " + market_text(c, q, pm),
                             "metadata": {"doc_id": f"{c.ticker}-quote", "title": "Market data", "section": q["source"], "content_type": "analysis",
                                          "form": "quote", "filed": q["as_of"][:10]}, "score": 1.0})
        if fin_m:
            evidence.append({"id": "FINANCIALS", "content": "Financial summary (computed in code from XBRL data): " + financials_text(fin_m),
                             "metadata": {"doc_id": f"{c.ticker}-xbrl", "title": "Structured financials", "section": "XBRL facts",
                                          "content_type": "analysis", "form": "XBRL", "filed": ""}, "score": 1.0})
        for key in ("business", "mdna", "risks", "events"):
            for h in d.get("filings", {}).get(key, []):
                if h["id"] not in {e["id"] for e in evidence}:
                    evidence.append(h)
        numbered = "\n\n".join(f"[{i}] {e['content']}" for i, e in enumerate(evidence, start=1))
        msgs = get_template("briefing").format_messages(headings="\n".join(f"## {h}" for h in SECTIONS), company=f"{c.name} ({c.ticker})",
                                                        evidence=numbered, style_instructions=STYLES[role.style])
        text, used = _llm(msgs, _extractive(evidence))
        sections, tidy_notes = tidy_sections(text, parse_sections(text, SECTIONS), MAX_BULLETS)
        return {"evidence": evidence, "briefing": {"sections": sections, "llm": used, "price_metrics": pm}, "notes": state["notes"] + tidy_notes,
                "trace": [f"write_briefing: {len(evidence)} evidence items, llm={used}"]}

    def review(state: State) -> dict:
        c, d = _company(state), state["data"]
        evidence = "\n".join(e["content"] for e in state["evidence"])
        chk = compliance_review(state["briefing"]["sections"], evidence, state["request"])   # review the text as written
        sections, backfilled = attribute_citations(chk.sections, state["evidence"])
        notes = list(state.get("notes", []))
        if chk.removed:
            notes.append(f"Compliance review removed {len(chk.removed)} statement(s) containing recommendation language.")
        if not chk.passed:
            notes.append("Some figures could not be matched to the sources - verify before use.")
        q = d.get("quote")
        briefing = {"company": c.__dict__, "as_of": date.today().isoformat(), "data_source": state["source"],
                    "quote": {k: v for k, v in (q or {}).items() if k != "weekly_closes"}, "weekly_closes": (q or {}).get("weekly_closes", []),
                    "price_metrics": state["briefing"]["price_metrics"], "financials": d.get("financials"), "metrics": d.get("metrics"),
                    "sections": sections, "llm_written": state["briefing"]["llm"], "citations_backfilled": backfilled, "removed_statements": chk.removed,
                    "notes": notes, "disclaimer": DISCLAIMER}
        cites = _citations(state["evidence"])
        return {"briefing": briefing, "answer": render_markdown(briefing, cites), "citations": cites, "outcome": "answered",
                "guardrail": {**state.get("guardrail", {}), "output_issues": chk.issues}, "trace": [f"compliance_review: {chk.issues or 'pass'}"]}

    # ------------------------------------------------------------ quote-only and follow-up paths
    def render_quote(state: State) -> dict:
        c, q = _company(state), state["data"].get("quote")
        if not q:
            return {"outcome": "unavailable", "answer": "Quote unavailable.", "trace": ["render_quote: none"]}
        pm = price_metrics(q, None, None)
        return {"answer": f"{c.name} ({c.ticker}): {market_text(c, q, pm)}", "briefing": {"quote": {k: v for k, v in q.items() if k != "weekly_closes"},
                "price_metrics": pm}, "outcome": "answered", "citations": [], "trace": ["render_quote"]}

    def retrieve(state: State) -> dict:
        hits = store.search(state["request"], s.top_k, {"ticker": _company(state).ticker})
        ctx = [h for h in hits if h["score"] >= s.min_relevance]
        return {"hits": hits, "context": ctx, "trace": [f"retrieve: {len(hits)} chunks, {len(ctx)} relevant"]}

    def answer(state: State) -> dict:
        c, ctx = _company(state), state["context"]
        if not ctx:
            return {"answer": "The filings I can access do not cover this.", "citations": [], "outcome": "no_answer", "trace": ["answer: no context"]}
        numbered = "\n\n".join(f"[{i}] {h['content']}" for i, h in enumerate(ctx, start=1))
        text, used = _llm(get_template("qa").format_messages(company=f"{c.name} ({c.ticker})", question=state["request"], context=numbered),
                          "Most relevant filing excerpts:\n" + "\n".join(f"[{i}] {h['content'][:300]}" for i, h in enumerate(ctx[:3], start=1)))
        issues = check_answer(text, "\n".join(h["content"] for h in ctx), state["request"])
        if "advice_language" in issues:
            text = "The answer contained recommendation language and was withheld. " + "Please rephrase the question as a factual one."
        elif issues:
            text += "\n\nNote: some figures could not be matched to the filings - verify before use."
        return {"answer": text, "citations": _citations(ctx), "outcome": "answered",
                "guardrail": {**state.get("guardrail", {}), "output_issues": issues}, "trace": [f"answer: llm={used} issues={issues or 'none'}"]}

    def finish(state: State) -> dict:
        return {"outcome": state.get("outcome") or "blocked", "citations": [], "trace": ["finish"]}

    g = StateGraph(State)
    for name, fn in [("guard_input", guard_input), ("resolve_company", resolve_company), ("authorize", authorize),
                     ("prepare_filings", prepare_filings), ("quote_agent", quote_agent), ("financials_agent", financials_agent),
                     ("filings_agent", filings_agent), ("write_briefing", write_briefing), ("compliance_review", review),
                     ("render_quote", render_quote), ("retrieve", retrieve), ("answer", answer), ("finish", finish)]:
        g.add_node(name, fn)
    g.add_edge(START, "guard_input")
    g.add_conditional_edges("guard_input", lambda st: "finish" if st.get("blocked") else "resolve_company", ["finish", "resolve_company"])
    g.add_edge("resolve_company", "authorize")

    def route(st: State) -> str | list[str]:
        if st.get("outcome"):
            return "finish"
        task = st.get("task", "briefing")
        return "quote_agent" if task == "quote" else "prepare_filings"

    g.add_conditional_edges("authorize", route, ["finish", "quote_agent", "prepare_filings"])
    g.add_conditional_edges("prepare_filings", lambda st: "retrieve" if st.get("task") == "qa" else ["quote_agent", "financials_agent", "filings_agent"],
                            ["retrieve", "quote_agent", "financials_agent", "filings_agent"])
    g.add_conditional_edges("quote_agent", lambda st: "render_quote" if st.get("task") == "quote" else "write_briefing",
                            ["render_quote", "write_briefing"])
    g.add_edge("financials_agent", "write_briefing")
    g.add_edge("filings_agent", "write_briefing")
    g.add_edge("write_briefing", "compliance_review")
    g.add_edge("compliance_review", END)
    g.add_edge("render_quote", END)
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)
    g.add_edge("finish", END)
    return g.compile()


# ---------------------------------------------------------------- text helpers
def _fmt(v, suffix="", money=False):
    if v is None:
        return "n/a"
    return f"${v:,.1f} million" if money else f"{v:,}{suffix}"


def market_text(c: Company, q: dict, pm: dict) -> str:
    parts = [f"price {pm['price']} {q.get('currency', 'USD')} as of {q['as_of']} ({q['source']})"]
    if pm["change"] is not None:
        parts.append(f"change {pm['change']:+} ({pm['change_pct']:+}%) vs previous close {q['previous_close']}")
    if q.get("fifty_two_week_low") is not None:
        parts.append(f"52-week range {q['fifty_two_week_low']} - {q['fifty_two_week_high']} (price at {pm['range_position_pct']}% of the range)")
    if pm["one_year_return_pct"] is not None:
        parts.append(f"1-year price change {pm['one_year_return_pct']}%")
    if pm["market_cap_bn"]:
        parts.append(f"market capitalisation ${pm['market_cap_bn']} billion")
    parts.append(f"P/E on latest fiscal-year EPS {pm['pe_fy']}" if pm["pe_fy"] else f"P/E {pm['pe_note']}")
    return "; ".join(parts) + "."


def financials_text(m: dict) -> str:
    t = (f"FY{m['fiscal_year']} revenue {_fmt(m['revenue_m'], money=True)} (growth {_fmt(m['revenue_growth_pct'], '%')}); "
         f"gross margin {_fmt(m['gross_margin_pct'], '%')}; operating margin {_fmt(m['operating_margin_pct'], '%')}; "
         f"net income {_fmt(m['net_income_m'], money=True)} (net margin {_fmt(m['net_margin_pct'], '%')}); diluted EPS {m['eps_diluted']} "
         f"(change {_fmt(m['eps_growth_pct'], '%')}); R&D {_fmt(m['rd_pct_of_revenue'], '%')} of revenue; cash {_fmt(m['cash_m'], money=True)}; "
         f"total debt {_fmt(m['total_debt_m'], money=True)}.")
    if m.get("quarter"):
        t += (f" Latest quarter ({m['quarter']}): revenue {_fmt(m['quarter_revenue_m'], money=True)} (year-on-year "
              f"{_fmt(m['quarter_revenue_growth_pct'], '%')}); net income {_fmt(m['quarter_net_income_m'], money=True)} vs "
              f"{_fmt(m['quarter_prior_net_income_m'], money=True)}; diluted EPS {m['quarter_eps_diluted']} vs {m['quarter_prior_eps_diluted']}.")
    return t


_WORD = re.compile(r"[a-z0-9][a-z0-9/.%$-]{2,}")
_STOP = frozenset(["the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "has", "have", "its", "into", "than", "then", "over", "under", "each", "all", "any", "per", "not", "but", "which", "while", "their", "they", "them", "these", "those", "should", "would", "could", "about", "after", "before", "within", "company"])
CITE_RE = re.compile(r"\[\d+(?:\s*,\s*\d+)*\]")


def _terms(text: str) -> set[str]:
    return {w.strip(".") for w in _WORD.findall(text.lower()) if w not in _STOP}


def attribute_citations(sections: dict[str, list[str]], evidence: list[dict], min_overlap: float = 0.5) -> tuple[dict, int]:
    """Citation backfill: a bullet without [n] gets the evidence item sharing most of its terms; below `min_overlap`
    it is marked unattributed instead of guessed."""
    ev_terms = [_terms(e["content"]) for e in evidence]
    out, added = {}, 0
    for heading, bullets in sections.items():
        fixed = []
        for b in bullets:
            terms = _terms(b)
            if CITE_RE.search(b) or not terms or b.endswith(":") or b.startswith("Not covered"):
                fixed.append(b)
                continue
            scores = [len(terms & et) / len(terms) for et in ev_terms]
            best = max(range(len(scores)), key=scores.__getitem__) if scores else None
            if best is not None and scores[best] >= min_overlap:
                fixed.append(f"{b} [{best + 1}]")
                added += 1
            else:
                fixed.append(f"{b} (unattributed)")
        out[heading] = fixed
    return out, added


def parse_sections(text: str, headings: list[str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {h: [] for h in headings}
    current = None
    for line in text.splitlines():
        m = re.match(r"^\s*#{1,4}\s*(.+?)\s*:?\s*$", line)
        if m:
            name = m.group(1).strip().lower()
            current = next((h for h in headings if h.lower() in name or name in h.lower()), None)
            continue
        item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s+", "", line).strip()
        if current and item:
            out[current].append(item)
    return out


def tidy_sections(text: str, sections: dict[str, list[str]], max_bullets: int) -> tuple[dict[str, list[str]], list[str]]:
    """Enforce the briefing structure on small-model output: cap bullets per section, drop dangling list headers
    ("The target doses are:") left without items, and drop the last bullet if the generation was cut off mid-sentence
    (output-token limit)."""
    notes = []
    out = {h: list(b) for h, b in sections.items()}
    if not text.rstrip().endswith((".", "!", "?", ")", "]", "%")):
        last = next((h for h in reversed(list(out)) if out[h]), None)
        if last:
            out[last].pop()
            notes.append("The model's output was cut off; the incomplete last statement was removed.")
    for h, bullets in out.items():
        bullets = bullets[:max_bullets]
        while bullets and bullets[-1].endswith(":"):
            bullets.pop()
        out[h] = bullets
    return out, notes


def _extractive(evidence: list[dict]) -> str:
    def first(e):
        body = e["content"].split("\n", 1)[-1]
        return body.strip().split(". ")[0][:220]

    by_group = {g: [(i, e) for i, e in enumerate(evidence, start=1) if e["metadata"].get("group") == g] for g in ("business", "mdna", "risks", "events")}
    lines = {"Business overview": [f"- {first(e)} [{i}]" for i, e in by_group["business"][:2]],
             "Recent performance": [f"- See the computed financial summary [{i}]" for i, e in enumerate(evidence, start=1) if e["id"] == "FINANCIALS"]
             + [f"- {first(e)} [{i}]" for i, e in by_group["mdna"][:1]],
             "Key risks": [f"- {first(e)} [{i}]" for i, e in by_group["risks"][:3]],
             "Recent events": [f"- {first(e)} [{i}]" for i, e in by_group["events"][:2]],
             "What to watch": ["- Not covered by the available filings."]}
    return "\n".join(f"## {h}\n" + "\n".join(v or ["- Not covered by the available filings."]) for h, v in lines.items())


def _citations(items: list[dict]) -> list[dict]:
    return [{"ref": i, "doc_id": h["metadata"].get("doc_id"), "title": h["metadata"].get("title"), "section": h["metadata"].get("section"),
             "form": h["metadata"].get("form"), "filed": h["metadata"].get("filed"), "url": h["metadata"].get("url", ""),
             "content_type": h["metadata"].get("content_type"), "score": h.get("score", 0)} for i, h in enumerate(items, start=1)]


def render_markdown(b: dict, cites: list[dict]) -> str:
    c, q, pm, m = b["company"], b["quote"], b["price_metrics"], b["metrics"]
    lines = [f"# Stock briefing: {c['name']} ({c['ticker']})", f"_Prepared {b['as_of']} | data: {b['data_source']}_", ""]
    if q and pm:
        lines += ["## Snapshot", "| Price | Change | 52-week range | 1-year | Market cap | P/E (FY EPS) |", "|---|---|---|---|---|---|",
                  (f"| {pm['price']} {q.get('currency', '')} | {pm['change']:+} ({pm['change_pct']:+}%) | {q['fifty_two_week_low']} - "
                  f"{q['fifty_two_week_high']} | {pm['one_year_return_pct']}% | "
                  f"{'$' + str(pm['market_cap_bn']) + 'B' if pm['market_cap_bn'] else 'n/a'} | {pm['pe_fy'] or pm['pe_note']} |"),
                  f"_Quote as of {q['as_of']} - {q['source']}_", ""]
    if m:
        lines += ["## Key financials (from XBRL data)", (f"- FY{m['fiscal_year']} revenue {_fmt(m['revenue_m'], money=True)}, growth "
                  f"{_fmt(m['revenue_growth_pct'], '%')}; operating margin {_fmt(m['operating_margin_pct'], '%')}; net income "
                  f"{_fmt(m['net_income_m'], money=True)}; diluted EPS {m['eps_diluted']}")]
        if m.get("quarter"):
            lines.append(f"- {m['quarter']}: revenue {_fmt(m['quarter_revenue_m'], money=True)} ({_fmt(m['quarter_revenue_growth_pct'], '%')} "
                         f"year-on-year); diluted EPS {m['quarter_eps_diluted']} vs {m['quarter_prior_eps_diluted']}")
        lines.append("")
    for heading, bullets in b["sections"].items():
        lines += [f"## {heading}"] + [f"- {x}" for x in (bullets or ["Not covered by the available filings."])] + [""]
    lines += ["## Sources"] + [f"[{x['ref']}] {x['title']} > {x['section']}" + (f" ({x['url']})" if str(x.get("url", "")).startswith("http") else "")
                               for x in cites] + [""]
    lines += [f"> {n}" for n in b["notes"]] + [f"> {b['disclaimer']}"]
    return "\n".join(lines)
