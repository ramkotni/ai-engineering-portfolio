r"""Single-agent RAG workflow (LangGraph). One knowledge domain, three tasks - no need for multiple agents.

  START -> guard_input --blocked--> finish
          classify_task (qa | summarize | search) -> authorize (task + clearance) --denied--> finish
          retrieve (classification filter BEFORE ranking) -> grade --nothing relevant--> no_answer
          generate (versioned prompt template; search needs no LLM) -> verify -> END
"""

import logging
import operator
import re
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel

from supplykb import rbac
from supplykb.config import Settings, get_settings
from supplykb.guardrails import check_input, check_output
from supplykb.prompts import SUMMARY_STYLES, get_template

log = logging.getLogger(__name__)
DOC_ID = re.compile(r"\b(SOP-CC-001|DEV-2026-014|SUP-QUAL-2026|GDP-POL-001)\b", re.IGNORECASE)
DOC_KEYWORDS = {"SOP-CC-001": ("cold chain", "shipping procedure", "sop"), "DEV-2026-014": ("deviation", "excursion report"),
                "SUP-QUAL-2026": ("supplier",), "GDP-POL-001": ("good distribution", "gdp", "policy")}


class State(TypedDict, total=False):
    question: str
    role: str
    task: str
    doc_id: str
    style: str
    blocked: bool
    guardrail: dict
    hits: list[dict]
    context: list[dict]
    answer: str
    citations: list[dict]
    outcome: str
    trace: Annotated[list[str], operator.add]


def classify(question: str) -> tuple[str, str | None]:
    q = question.lower().strip()
    m = DOC_ID.search(question)
    doc = m.group(1).upper() if m else next((d for d, kws in DOC_KEYWORDS.items() if any(k in q for k in kws)), None)
    if q.startswith(("summar", "give me a summary", "summary of", "brief me on")) or " summary of " in q:
        return "summarize", doc
    if q.startswith(("find ", "search ", "list ", "which documents", "show documents")):
        return "search", None
    return "qa", None


def build_graph(llm: BaseChatModel | None = None, retrievers: dict | None = None, settings: Settings | None = None):
    from langgraph.graph import END, START, StateGraph

    s = settings or get_settings()
    if llm is None:
        from supplykb.llm import get_chat_model

        llm = get_chat_model()
    if retrievers is None:
        from supplykb.retrieval import get_retrievers

        retrievers = get_retrievers()
    store = retrievers["documents"]

    def _llm(messages, fallback: str) -> tuple[str, bool]:
        try:
            text = str(llm.invoke(messages).content).strip()
            return (text, True) if text else (fallback, False)
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM failed; extractive fallback: %s", exc)
            return fallback, False

    def guard_input(state: State) -> dict:
        chk = check_input(state["question"], s.max_question_chars)
        return {"question": chk.question, "blocked": not chk.allowed, "answer": chk.message or "",
                "guardrail": {"input_category": chk.category, "input_flags": chk.flags},
                "trace": [f"guard_input: {chk.category or 'pass'}"]}

    def classify_task(state: State) -> dict:
        task, doc = classify(state["question"])
        task = state.get("task") or task
        doc = state.get("doc_id") or doc
        return {"task": task, "doc_id": doc or "", "trace": [f"classify_task: {task} doc={doc}"]}

    def authorize(state: State) -> dict:
        role = rbac.get_role(state["role"])
        if not role.allows(state["task"]):
            return {"outcome": "denied", "answer": f"Your role ({role.name}) cannot use '{state['task']}'.",
                    "trace": ["authorize: DENIED task"]}
        if state["task"] == "summarize":
            if not state.get("doc_id"):
                return {"outcome": "denied", "answer": "Which document? Name it, e.g. 'Summarize DEV-2026-014'.",
                        "trace": ["authorize: no document"]}
            probe = store.search(state["doc_id"], 1, {"doc_id": state["doc_id"]})
            if probe and not role.can_see(probe[0]["metadata"]["classification"]):
                return {"outcome": "denied", "answer": f"{state['doc_id']} is {probe[0]['metadata']['classification']}; "
                                                        f"your clearance is {role.clearance}.", "trace": ["authorize: DENIED clearance"]}
        return {"trace": [f"authorize: {role.name} clearance={role.clearance}"]}

    def retrieve(state: State) -> dict:
        role = rbac.get_role(state["role"])
        where: dict = {"classification": role.visible_levels}   # access control BEFORE ranking
        if state["task"] == "summarize":
            hits = store.search(state["doc_id"] + " " + state["question"], 40, {**where, "doc_id": state["doc_id"]})
            hits.sort(key=lambda h: _order(h["id"]))
        else:
            hits = store.search(state["question"], s.top_k, where)
            lots = set(re.findall(r"\bLOT-\d+\b", state["question"].upper()))
            for lot in lots:  # exact lookup of structured records mentioned by ID
                hits += [h for h in store.search(lot, 1, {**where, "lot_id": lot}) if h["id"] not in {x["id"] for x in hits}]
        return {"hits": hits, "trace": [f"retrieve: {len(hits)} chunks {[h['id'] for h in hits][:8]}"]}

    def grade(state: State) -> dict:
        hits = state["hits"]
        ctx = hits if state["task"] == "summarize" else [h for h in hits if h["score"] >= s.min_relevance]
        return {"context": ctx, "trace": [f"grade: {len(ctx)} relevant"]}

    def generate(state: State) -> dict:
        ctx = state["context"]
        cites = [{"ref": i, "doc_id": h["metadata"]["doc_id"], "title": h["metadata"]["title"], "section": h["metadata"]["section"],
                  "content_type": h["metadata"]["content_type"], "classification": h["metadata"]["classification"],
                  "image_path": h["metadata"].get("image_path"), "score": h["score"]} for i, h in enumerate(ctx, start=1)]
        if state["task"] == "search":
            docs = {}
            for h in ctx:
                docs.setdefault(h["metadata"]["doc_id"], h)
            answer = "Matching documents:\n" + "\n".join(
                f"- {d} - {h['metadata']['title']} > {h['metadata']['section']} ({h['metadata']['classification']})" for d, h in docs.items())
            return {"answer": answer, "citations": cites, "trace": ["generate: search listing (no LLM)"]}
        if state["task"] == "summarize":
            style = state.get("style") or "brief"
            document = "\n\n".join(h["content"] for h in ctx)
            msgs = get_template("summarize").format_messages(style_instructions=SUMMARY_STYLES[style], doc_id=state["doc_id"],
                                                             title=ctx[0]["metadata"]["title"], document=document)
            answer, used = _llm(msgs, "Key sections:\n" + "\n".join(f"- {h['content'][:200]}" for h in ctx[:4]))
            return {"answer": answer, "citations": cites, "trace": [f"generate: summarize style={style} llm={used}"]}
        context = "\n\n".join(f"[{i}] {h['content']}" for i, h in enumerate(ctx, start=1))
        answer, used = _llm(get_template("qa").format_messages(question=state["question"], context=context),
                            "Most relevant passages:\n" + "\n".join(f"[{i}] {h['content'][:300]}" for i, h in enumerate(ctx[:3], start=1)))
        return {"answer": answer, "citations": cites, "trace": [f"generate: qa llm={used}"]}

    def verify(state: State) -> dict:
        context = "\n".join(h["content"] for h in state["context"])
        chk = check_output(state["answer"], context, state["question"])
        answer = chk.answer if chk.passed else chk.answer + "\n\nNote: some values or IDs could not be matched to the source documents - verify before use."
        return {"answer": answer, "outcome": "answered", "guardrail": {**state.get("guardrail", {}), "output_issues": chk.issues},
                "trace": [f"verify: {chk.issues or 'pass'}"]}

    def no_answer(state: State) -> dict:
        return {"answer": "The documents I can access do not cover this. Contact Quality Assurance for controlled information.",
                "citations": [], "outcome": "no_answer", "trace": ["no_answer"]}

    def finish(state: State) -> dict:
        return {"outcome": state.get("outcome") or "blocked", "citations": [], "trace": ["finish"]}

    g = StateGraph(State)
    for name, fn in [("guard_input", guard_input), ("classify_task", classify_task), ("authorize", authorize), ("retrieve", retrieve),
                     ("grade", grade), ("generate", generate), ("verify", verify), ("no_answer", no_answer), ("finish", finish)]:
        g.add_node(name, fn)
    g.add_edge(START, "guard_input")
    g.add_conditional_edges("guard_input", lambda st: "finish" if st.get("blocked") else "classify_task", ["finish", "classify_task"])
    g.add_edge("classify_task", "authorize")
    g.add_conditional_edges("authorize", lambda st: "finish" if st.get("outcome") == "denied" else "retrieve", ["finish", "retrieve"])
    g.add_edge("retrieve", "grade")
    g.add_conditional_edges("grade", lambda st: "generate" if st.get("context") else "no_answer", ["generate", "no_answer"])
    g.add_edge("generate", "verify")
    g.add_edge("verify", END)
    g.add_edge("no_answer", END)
    g.add_edge("finish", END)
    return g.compile()


def _order(chunk_id: str) -> tuple:
    tail = chunk_id.split("::")[-1]
    return (0, int(tail)) if tail.isdigit() else (1, tail)
