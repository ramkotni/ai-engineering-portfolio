r"""Feasibility Advisor - a small LangGraph workflow on top of the ML model.

  START -> guard_notes (prompt-injection check on free text) -> predict (sklearn tool)
        -> retrieve_playbook (BM25 over the delivery playbook, keyed by the negative drivers)
        -> advise (LLM narrative; deterministic fallback) -> guard_output (numeric grounding) -> END

Why this much LLM and no more: the decision (probability) is made by an interpretable model; the LLM only turns
the model's drivers and the playbook into readable advice. RAG here is a 7-section playbook, so BM25 is
enough - no vector store needed.
"""

import logging
import operator
import re
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from feasibility.config import get_settings
from feasibility.predict import ProjectInput, predict

log = logging.getLogger(__name__)
INJECTION = re.compile(r"\b(ignore|disregard)\b.{0,30}\b(instructions?|rules?|prompts?)|\b(system prompt|jailbreak)\b", re.IGNORECASE)
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
DRIVER_TO_SECTION = {"tech_readiness": "Low Technology Readiness", "complexity": "High Complexity",
                     "staffing_pressure": "Resource Constraints", "resource_availability": "Resource Constraints",
                     "dependency_count": "Many Dependencies", "complexity_x_dependencies": "Many Dependencies",
                     "log_budget_per_week": "Thin Budget or Timeline", "timeline_weeks": "Thin Budget or Timeline",
                     "budget_usd": "Thin Budget or Timeline", "team_experience_years": "Inexperienced Team",
                     "experience_per_complexity": "Inexperienced Team", "stakeholder_count": "Large Stakeholder Groups"}


class State(TypedDict, total=False):
    project: dict
    notes: str
    blocked: bool
    prediction: dict
    playbook: list[str]
    advice: str
    guardrail: dict
    trace: Annotated[list[str], operator.add]


def playbook_sections() -> dict[str, str]:
    text = (get_settings().data_dir / "delivery_playbook.md").read_text(encoding="utf-8")
    parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
    return {p.splitlines()[0].strip(): "## " + p.strip() for p in parts}


def build_advisor(llm: BaseChatModel | None = None):
    from langgraph.graph import END, START, StateGraph

    if llm is None:
        from langchain_ollama import ChatOllama

        s = get_settings()
        llm = ChatOllama(model=s.ollama_chat_model, base_url=s.ollama_base_url, temperature=0, num_predict=400,
                         num_thread=s.ollama_num_thread, keep_alive=s.ollama_keep_alive)
    sections = playbook_sections()

    def guard_notes(state: State) -> dict:
        bad = bool(INJECTION.search(state.get("notes", "")))
        return {"blocked": bad, "guardrail": {"notes_injection": bad},
                "advice": "Notes were rejected (they look like instructions to the assistant)." if bad else "",
                "trace": [f"guard_notes: {'BLOCKED' if bad else 'pass'}"]}

    def predict_node(state: State) -> dict:
        p = predict(ProjectInput(**state["project"]))
        return {"prediction": p, "trace": [f"predict: p={p['feasibility_probability']} {p['risk_band']}"]}

    def retrieve_playbook(state: State) -> dict:
        names = [DRIVER_TO_SECTION.get(d["feature"]) for d in state["prediction"]["top_negative_drivers"]]
        chosen = list(dict.fromkeys(n for n in names if n and n in sections))
        return {"playbook": [sections[n] for n in chosen], "trace": [f"retrieve_playbook: {chosen}"]}

    def advise(state: State) -> dict:
        p = state["prediction"]
        facts = (f"Feasibility probability: {p['feasibility_probability']} ({p['risk_band']}).\n"
                 f"Budget per week: {p['budget_per_week_usd']} USD.\n"
                 "Negative drivers: " + "; ".join(f"{d['description']} ({d['contribution']})" for d in p["top_negative_drivers"]) + "\n"
                 "Positive drivers: " + "; ".join(f"{d['description']} ({d['contribution']})" for d in p["top_positive_drivers"]) + "\n"
                 + ("Warnings: " + "; ".join(p["ood_warnings"]) if p["ood_warnings"] else ""))
        project = "\n".join(f"{k}: {v}" for k, v in state["project"].items())
        fallback = (f"Feasibility {p['feasibility_probability']} ({p['risk_band']}). Main risks: "
                    + ", ".join(d["description"] for d in p["top_negative_drivers"])
                    + ".\n\n" + "\n\n".join(state["playbook"]))
        try:
            text = str(llm.invoke([
                SystemMessage(content="You advise a project intake board. Using ONLY the model output, project data and playbook "
                                      "excerpts, explain in 3-5 bullets why the project is or is not likely feasible and give "
                                      "2-4 mitigation actions from the playbook. Copy numbers exactly. Say this is decision "
                                      "support, not an approval."),
                HumanMessage(content=f"Project:\n{project}\n\nModel output:\n{facts}\n\nPlaybook:\n" + "\n\n".join(state["playbook"])),
            ]).content).strip() or fallback
            used = text != fallback
        except Exception as exc:  # noqa: BLE001
            log.warning("Advisor LLM failed: %s", exc)
            text, used = fallback, False
        return {"advice": text, "trace": [f"advise: llm={used}"], "guardrail": {**state.get("guardrail", {}), "facts": facts}}

    def guard_output(state: State) -> dict:
        evidence = state["guardrail"]["facts"] + "\n".join(f"{k} {v}" for k, v in state["project"].items()) + "\n".join(state["playbook"])
        allowed = {n.replace(",", "") for n in NUMBER.findall(evidence)}
        body = re.sub(r"^\s*\d+[.)]\s+", " ", state["advice"], flags=re.MULTILINE)
        unsupported = sorted({n.replace(",", "") for n in NUMBER.findall(body)} - allowed)
        advice = state["advice"] + ("\n\nNote: some figures could not be matched to the model output - verify." if unsupported else "")
        g = {k: v for k, v in state["guardrail"].items() if k != "facts"}
        return {"advice": advice, "guardrail": {**g, "unsupported_numbers": unsupported},
                "trace": [f"guard_output: {unsupported or 'pass'}"]}

    g = StateGraph(State)
    for name, fn in [("guard_notes", guard_notes), ("predict", predict_node), ("retrieve_playbook", retrieve_playbook),
                     ("advise", advise), ("guard_output", guard_output)]:
        g.add_node(name, fn)
    g.add_edge(START, "guard_notes")
    g.add_conditional_edges("guard_notes", lambda st: END if st.get("blocked") else "predict", [END, "predict"])
    g.add_edge("predict", "retrieve_playbook")
    g.add_edge("retrieve_playbook", "advise")
    g.add_edge("advise", "guard_output")
    g.add_edge("guard_output", END)
    return g.compile()
