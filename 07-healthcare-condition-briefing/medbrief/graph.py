r"""Condition-briefing workflow (LangGraph): a planner fans out to four section agents that run in parallel,
then one writer call turns their evidence into a structured briefing.

  START -> guard_input --blocked--> finish
           resolve_condition -> authorize (task, clearance, live-data) --denied / unknown--> finish
           task = qa       -> retrieve -> grade -> answer -> verify -> END
           task = briefing -> gather_trials (synthetic registry or live ClinicalTrials.gov)
                              -> [standard_of_care | pipeline | key_players | strategy]   (parallel)
                              -> write_briefing (one LLM call, numbered evidence) -> verify -> END

Deterministic code owns the facts: trial counts, phases, rankings and readout years are computed in
medbrief.trials; the LLM only writes prose around them and must cite evidence numbers.
"""

import logging
import operator
import re
from datetime import date
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel

from medbrief import rbac
from medbrief.conditions import CATALOGUE, adhoc, resolve
from medbrief.config import Settings, get_settings
from medbrief.guardrails import DISCLAIMER, check_input, check_output
from medbrief.prompts import SECTIONS, STRATEGY_SECTION, STYLES, get_template
from medbrief.trials import Trial, evidence_text, get_trials, key_players, pipeline_summary

log = logging.getLogger(__name__)
SOC_QUERIES = ["first-line treatment recommendations drug classes target doses", "treatment algorithm device therapy thresholds referral",
               "diagnosis criteria targets", "quality measures benchmarks"]
EMERGING_QUERIES = ["emerging therapies pipeline development late-stage", "pipeline by modality figure"]
MAX_BULLETS = 8                 # small models ignore "2-4 bullets"; the structure is enforced in code
STRATEGY_QUERIES = ["program position performance gap benchmark", "partnership and trial-site opportunities", "recommendations for leadership"]


def _merge(a: dict, b: dict) -> dict:
    return {**a, **b}


class State(TypedDict, total=False):
    request: str
    role: str
    task: str                       # briefing | qa
    source: str                     # synthetic | live
    condition: dict
    blocked: bool
    guardrail: dict
    trials: list[dict]
    trial_source: str
    sections: Annotated[dict, _merge]   # evidence from the parallel section agents
    hits: list[dict]
    context: list[dict]
    evidence: list[dict]
    briefing: dict
    answer: str
    citations: list[dict]
    outcome: str
    notes: list[str]
    trace: Annotated[list[str], operator.add]


def build_graph(llm: BaseChatModel | None = None, retrievers: dict | None = None, settings: Settings | None = None, trials_fn=None):
    from langgraph.graph import END, START, StateGraph

    s = settings or get_settings()
    if llm is None:
        from medbrief.llm import get_chat_model

        llm = get_chat_model()
    if retrievers is None:
        from medbrief.retrieval import get_retrievers

        retrievers = get_retrievers()
    store = retrievers["documents"]
    fetch_trials = trials_fn or (lambda cond, source: get_trials(cond, source, s))

    def _cond(state: State):
        c = state["condition"]
        return CATALOGUE.get(c["key"]) or adhoc(c["name"])

    def _search(queries: list[str], where: dict, k: int) -> list[dict]:
        seen: dict[str, dict] = {}
        for q in queries:
            for h in store.search(q, k, where):
                if h["id"] not in seen or h["score"] > seen[h["id"]]["score"]:
                    seen[h["id"]] = h
        return sorted(seen.values(), key=lambda h: h.get("rrf", 0), reverse=True)

    def _llm(messages, fallback: str) -> tuple[str, bool]:
        try:
            text = str(llm.invoke(messages).content).strip()
            return (text, True) if text else (fallback, False)
        except Exception as exc:  # noqa: BLE001 - the briefing degrades to extractive, never crashes
            log.warning("LLM failed; extractive fallback: %s", exc)
            return fallback, False

    # ------------------------------------------------------------ shared front end
    def guard_input(state: State) -> dict:
        chk = check_input(state["request"], s.max_question_chars)
        return {"request": chk.text, "blocked": not chk.allowed, "answer": chk.message or "", "notes": [],
                "guardrail": {"input_category": chk.category, "input_flags": chk.flags},
                "trace": [f"guard_input: {chk.category or 'pass'}"]}

    def resolve_condition(state: State) -> dict:
        cond = resolve(state["request"])
        if cond is None and state.get("task") == "briefing" and state.get("source") == "live":
            cond = adhoc(state["request"])
        return {"condition": {"key": cond.key, "name": cond.name} if cond else {},
                "trace": [f"resolve_condition: {cond.key if cond else 'none'}"]}

    def authorize(state: State) -> dict:
        role = rbac.get_role(state["role"])
        task = state.get("task", "briefing")
        if not role.allows(task):
            return {"outcome": "denied", "answer": f"Your role ({role.name}) cannot use '{task}'. Allowed: {', '.join(role.tasks)}.",
                    "trace": ["authorize: DENIED task"]}
        if task == "briefing" and not state.get("condition"):
            known = ", ".join(c.name for c in CATALOGUE.values())
            return {"outcome": "unknown_condition", "answer": f"No sources for that condition in the knowledge base. Available: {known}. "
                                                              "Roles with live-data access can brief any condition from ClinicalTrials.gov.",
                    "trace": ["authorize: unknown condition"]}
        notes = list(state.get("notes", []))
        source = state.get("source", s.trials_source)
        if source == "live" and not role.live_data:
            source = "synthetic"
            notes.append(f"Live trial data is not enabled for the {role.name} role; the synthetic registry was used.")
            if state["condition"].get("key") == "adhoc":
                return {"outcome": "denied", "answer": "This condition needs live trial data, which your role cannot use.",
                        "trace": ["authorize: DENIED live data"]}
        return {"source": source, "notes": notes, "trace": [f"authorize: {role.name} clearance={role.clearance} source={source}"]}

    # ------------------------------------------------------------ briefing path
    def gather_trials(state: State) -> dict:
        trials, used = fetch_trials(_cond(state), state["source"])
        return {"trials": [t.__dict__ for t in trials], "trial_source": used,
                "trace": [f"gather_trials: {len(trials)} from {used}"]}

    def standard_of_care(state: State) -> dict:
        cond, role = _cond(state), rbac.get_role(state["role"])
        hits = []
        if cond.guideline_docs:
            hits = _search(SOC_QUERIES, {"doc_id": list(cond.guideline_docs), "classification": role.visible_levels}, 4)[: s.briefing_k]
        return {"sections": {"standard_of_care": hits}, "trace": [f"standard_of_care: {len(hits)} guideline chunks"]}

    def pipeline(state: State) -> dict:
        cond, role = _cond(state), rbac.get_role(state["role"])
        summary = pipeline_summary([Trial(**t) for t in state["trials"]])
        hits = []
        if cond.guideline_docs:
            hits = _search(EMERGING_QUERIES, {"doc_id": list(cond.guideline_docs), "classification": role.visible_levels}, 2)[:2]
        return {"sections": {"pipeline": {"summary": summary, "hits": hits}},
                "trace": [f"pipeline: {summary['active_programs']} active, {len(summary['late_stage'])} late-stage"]}

    def players(state: State) -> dict:
        kp = key_players([Trial(**t) for t in state["trials"]])
        return {"sections": {"key_players": kp},
                "trace": [f"key_players: {len(kp['companies'])} companies, {len(kp['institutions'])} institutions"]}

    def strategy(state: State) -> dict:
        role, cond = rbac.get_role(state["role"]), _cond(state)
        if not role.can_see("internal") or cond.key == "adhoc":
            return {"sections": {"strategy": []}, "trace": ["strategy: skipped (not cleared for internal documents)"
                                                            if not role.can_see("internal") else "strategy: no internal sources"]}
        hits = _search(STRATEGY_QUERIES, {"classification": "internal", "condition": [cond.key, "all"]}, 2)[:3]
        return {"sections": {"strategy": hits}, "trace": [f"strategy: {len(hits)} internal chunks"]}

    def write_briefing(state: State) -> dict:
        role, cond, sec = rbac.get_role(state["role"]), _cond(state), state["sections"]
        evidence: list[dict] = []
        for h in sec.get("standard_of_care", []) + sec["pipeline"]["hits"] + sec.get("strategy", []):
            if h["id"] not in {e.get("id") for e in evidence}:
                evidence.append({"id": h["id"], "content": h["content"], "metadata": h["metadata"], "score": h["score"]})
        registry_text = evidence_text(sec["pipeline"]["summary"], sec["key_players"], state["trial_source"])
        evidence.append({"id": "REGISTRY-ANALYSIS", "content": "Trial registry analysis (computed in code)\n" + registry_text,
                         "metadata": {"doc_id": "REG-2026" if state["trial_source"] == "synthetic registry" else "ClinicalTrials.gov",
                                      "title": "Trial registry analysis", "section": state["trial_source"], "content_type": "analysis",
                                      "classification": "public"}, "score": 1.0})
        headings = SECTIONS + ([STRATEGY_SECTION] if sec.get("strategy") else [])
        numbered = "\n\n".join(f"[{i}] {e['content']}" for i, e in enumerate(evidence, start=1))
        msgs = get_template("briefing").format_messages(headings="\n".join(f"## {h}" for h in headings), condition=cond.name,
                                                        evidence=numbered, style_instructions=STYLES[role.style])
        text, used = _llm(msgs, _extractive(evidence, headings, len(evidence)))
        sections, tidy_notes = tidy_sections(text, parse_sections(text, headings), MAX_BULLETS)
        return {"evidence": evidence, "briefing": {"sections": sections, "raw": text, "llm": used}, "notes": state["notes"] + tidy_notes,
                "trace": [f"write_briefing: {len(evidence)} evidence items, llm={used}"]}

    def verify_briefing(state: State) -> dict:
        evidence = "\n".join(e["content"] for e in state["evidence"])
        chk = check_output(state["briefing"]["raw"], evidence, state["request"])
        notes = list(state.get("notes", []))
        if not chk.passed:
            notes.append("Some values or IDs could not be matched to the sources - verify before use.")
        sec = state["sections"]
        sections, backfilled = attribute_citations(state["briefing"]["sections"], state["evidence"])
        briefing = {
            "condition": state["condition"]["name"], "as_of": date.today().isoformat(), "trial_source": state["trial_source"],
            "sections": sections, "llm_written": state["briefing"]["llm"], "citations_backfilled": backfilled,
            "pipeline": sec["pipeline"]["summary"], "key_players": sec["key_players"], "notes": notes, "disclaimer": DISCLAIMER,
        }
        cites = _citations(state["evidence"])
        return {"briefing": briefing, "answer": render_markdown(briefing, cites), "citations": cites, "outcome": "answered",
                "guardrail": {**state.get("guardrail", {}), "output_issues": chk.issues}, "trace": [f"verify: {chk.issues or 'pass'}"]}

    # ------------------------------------------------------------ follow-up question path
    def retrieve(state: State) -> dict:
        role = rbac.get_role(state["role"])
        where: dict = {"classification": role.visible_levels}          # access control BEFORE ranking
        if state.get("condition"):
            where["condition"] = [state["condition"]["key"], "all"]
        hits = store.search(state["request"], s.top_k, where)
        for tid in set(re.findall(r"\bSYN-(?:HF|DM)-\d+\b", state["request"].upper())):     # exact lookup by trial ID
            hits += [h for h in store.search(tid, 1, {**where, "trial_id": tid}) if h["id"] not in {x["id"] for x in hits}]
        return {"hits": hits, "trace": [f"retrieve: {len(hits)} chunks {[h['id'] for h in hits][:8]}"]}

    def grade(state: State) -> dict:
        ctx = [h for h in state["hits"] if h["score"] >= s.min_relevance]
        return {"context": ctx, "trace": [f"grade: {len(ctx)} relevant"]}

    def answer(state: State) -> dict:
        ctx = state["context"]
        numbered = "\n\n".join(f"[{i}] {h['content']}" for i, h in enumerate(ctx, start=1))
        text, used = _llm(get_template("qa").format_messages(question=state["request"], context=numbered),
                          "Most relevant passages:\n" + "\n".join(f"[{i}] {h['content'][:300]}" for i, h in enumerate(ctx[:3], start=1)))
        return {"answer": text, "citations": _citations(ctx), "trace": [f"answer: llm={used}"]}

    def verify_answer(state: State) -> dict:
        chk = check_output(state["answer"], "\n".join(h["content"] for h in state["context"]), state["request"])
        text = chk.text if chk.passed else chk.text + "\n\nNote: some values or IDs could not be matched to the sources - verify before use."
        return {"answer": text, "outcome": "answered", "guardrail": {**state.get("guardrail", {}), "output_issues": chk.issues},
                "trace": [f"verify: {chk.issues or 'pass'}"]}

    def no_answer(state: State) -> dict:
        return {"answer": "The sources I can access do not cover this.", "citations": [], "outcome": "no_answer", "trace": ["no_answer"]}

    def finish(state: State) -> dict:
        return {"outcome": state.get("outcome") or "blocked", "citations": [], "trace": ["finish"]}

    g = StateGraph(State)
    for name, fn in [("guard_input", guard_input), ("resolve_condition", resolve_condition), ("authorize", authorize),
                     ("gather_trials", gather_trials), ("standard_of_care", standard_of_care), ("pipeline", pipeline),
                     ("key_players", players), ("strategy", strategy), ("write_briefing", write_briefing),
                     ("verify_briefing", verify_briefing), ("retrieve", retrieve), ("grade", grade), ("answer", answer),
                     ("verify_answer", verify_answer), ("no_answer", no_answer), ("finish", finish)]:
        g.add_node(name, fn)
    g.add_edge(START, "guard_input")
    g.add_conditional_edges("guard_input", lambda st: "finish" if st.get("blocked") else "resolve_condition", ["finish", "resolve_condition"])
    g.add_edge("resolve_condition", "authorize")
    g.add_conditional_edges("authorize", lambda st: "finish" if st.get("outcome") else
                            ("gather_trials" if st.get("task", "briefing") == "briefing" else "retrieve"),
                            ["finish", "gather_trials", "retrieve"])
    for agent in ("standard_of_care", "pipeline", "key_players", "strategy"):      # parallel fan-out
        g.add_edge("gather_trials", agent)
    g.add_edge(["standard_of_care", "pipeline", "key_players", "strategy"], "write_briefing")   # join
    g.add_edge("write_briefing", "verify_briefing")
    g.add_edge("verify_briefing", END)
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", lambda st: "answer" if st.get("context") else "no_answer", ["answer", "no_answer"])
    g.add_edge("answer", "verify_answer")
    g.add_edge("verify_answer", END)
    g.add_edge("no_answer", END)
    g.add_edge("finish", END)
    return g.compile()


# ---------------------------------------------------------------- helpers
_WORD = re.compile(r"[a-z0-9][a-z0-9/.%-]{2,}")
_STOP = frozenset(["the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "has", "have", "its", "into", "than", "then", "over", "under", "each", "all", "any", "per", "not", "but", "which", "while", "their", "they", "them", "these", "those", "should", "would", "could", "about", "after", "before", "within"])


def _terms(text: str) -> set[str]:
    return {w.strip(".") for w in _WORD.findall(text.lower()) if w not in _STOP}


def attribute_citations(sections: dict[str, list[str]], evidence: list[dict], min_overlap: float = 0.5) -> tuple[dict, int]:
    """Citation backfill: a bullet without [n] gets the evidence item that shares most of its terms (numbers, drug
    names, IDs). Below `min_overlap` it is marked unattributed instead of guessed. Small models often skip citations;
    this keeps every statement traceable."""
    ev_terms = [_terms(e["content"]) for e in evidence]
    out, added = {}, 0
    for heading, bullets in sections.items():
        fixed = []
        for b in bullets:
            terms = _terms(b)
            if CITE_RE.search(b) or not terms or b.endswith(":"):
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


CITE_RE = re.compile(r"\[\d+(?:\s*,\s*\d+)*\]")


def parse_sections(text: str, headings: list[str]) -> dict[str, list[str]]:
    """'## Heading' blocks -> {heading: [bullets]}. Unknown headings are ignored; missing ones become empty lists."""
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


def _extractive(evidence: list[dict], headings: list[str], registry_ref: int) -> str:
    """Fallback when the LLM is unavailable: first sentences of the top evidence per section."""
    def first(e):
        body = e["content"].split("\n", 1)[-1]
        return re.split(r"(?<=[.!?])\s", body.strip())[0][:220]

    soc = [f"- {first(e)} [{i}]" for i, e in enumerate(evidence, start=1) if e["metadata"].get("content_type") in ("text", "table", "mixed")][:3]
    reg = f"[{registry_ref}]"
    parts = {"Executive summary": [f"- See the registry analysis and guideline excerpts below {reg}."],
             "Standard of care": soc or ["- Not covered by the available sources."],
             "Emerging treatments": [f"- Late-stage programs and expected readouts are listed in the registry analysis {reg}."],
             "Key companies and institutions": [f"- Ranked by active programs in the registry analysis {reg}."],
             STRATEGY_SECTION: [f"- {first(e)} [{i}]" for i, e in enumerate(evidence, start=1) if e["metadata"].get("classification") == "internal"][:3]}
    return "\n".join(f"## {h}\n" + "\n".join(parts[h]) for h in headings)


def _citations(items: list[dict]) -> list[dict]:
    return [{"ref": i, "doc_id": h["metadata"].get("doc_id"), "title": h["metadata"].get("title"), "section": h["metadata"].get("section"),
             "content_type": h["metadata"].get("content_type"), "classification": h["metadata"].get("classification"),
             "image_path": h["metadata"].get("image_path"), "score": h.get("score", 0)} for i, h in enumerate(items, start=1)]


def render_markdown(b: dict, cites: list[dict]) -> str:
    lines = [f"# Condition briefing: {b['condition']}", f"_As of {b['as_of']} | trial data: {b['trial_source']}_", ""]
    for heading, bullets in b["sections"].items():
        lines += [f"## {heading}"] + [f"- {x}" for x in (bullets or ["Not covered by the available sources."])] + [""]
        if heading == "Emerging treatments" and b["pipeline"]["late_stage"]:
            lines += ["| Trial | Intervention | Phase | Status | Sponsor | Primary completion |", "|---|---|---|---|---|---|"]
            lines += [f"| {t['trial_id']} | {t['intervention']} | {t['phase']} | {t['status']} | {t['sponsor']} | {t['primary_completion']} |"
                      for t in b["pipeline"]["late_stage"][:8]] + [""]
        if heading == "Key companies and institutions":
            for label, rows in (("Companies", b["key_players"]["companies"][:5]), ("Institutions", b["key_players"]["institutions"][:5])):
                if rows:
                    lines += [f"**{label}** - " + "; ".join(f"{r['name']} ({r['active_programs']} active, most advanced {r['most_advanced_phase']})"
                                                         for r in rows), ""]
    lines += ["## Sources"] + [f"[{c['ref']}] {c['doc_id']} - {c['title']} > {c['section']} ({c['content_type']})" for c in cites] + [""]
    lines += [f"> {n}" for n in b["notes"]] + [f"> {b['disclaimer']}"]
    return "\n".join(lines)
