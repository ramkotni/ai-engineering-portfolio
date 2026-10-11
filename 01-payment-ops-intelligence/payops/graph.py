r"""Multi-agent LangGraph: supervisor pattern.

  START -> guard_input --blocked--> finish -> END
              | ok
          intent_agent -> authorize --denied--> finish
              | plan, e.g. rca = [search_agent, rca_agent, recommendation_agent]
          supervisor <-> search_agent | rca_agent | recommendation_agent | trend_agent | summary_agent
              | plan done
          compose -> guard_output -> END

The supervisor pops the next agent from the plan; every agent returns to the supervisor.
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from payops import rbac
from payops.agents import PaymentAgents
from payops.config import Settings, get_settings
from payops.guardrails import check_input, check_output


def merge(a: dict | None, b: dict | None) -> dict:
    return {**(a or {}), **(b or {})}


class State(TypedDict, total=False):
    question: str
    role: str
    blocked: bool
    guardrail: dict
    intent: dict
    plan: list[str]
    step: int
    outputs: Annotated[dict, merge]   # agent name -> output
    answer: str
    citations: list[str]
    outcome: str                      # answered | blocked | denied
    trace: Annotated[list[str], operator.add]


PLANS = {
    "search": ["search_agent"],
    "rca": ["search_agent", "rca_agent"],
    "recommendation": ["search_agent", "recommendation_agent"],
    "trend": ["trend_agent"],
    "summary": ["trend_agent", "summary_agent"],
}


def build_graph(llm: BaseChatModel | None = None, retrievers: dict | None = None, settings: Settings | None = None):
    s = settings or get_settings()
    if llm is None:
        from payops.llm import get_chat_model

        llm = get_chat_model()
    if retrievers is None:
        from payops.retrieval import get_retrievers

        retrievers = get_retrievers()
    agents = PaymentAgents(llm, retrievers, s)

    def guard_input(state: State) -> dict:
        chk = check_input(state["question"], s.max_question_chars)
        return {"question": chk.question, "blocked": not chk.allowed, "answer": chk.message or "",
                "guardrail": {"input_category": chk.category, "input_flags": chk.flags}, "step": 0,
                "trace": [f"guard_input: {chk.category or 'pass'} {chk.flags}"]}

    def intent_agent(state: State) -> dict:
        d, method = agents.classify(state["question"])
        return {"intent": {**d.model_dump(), "method": method},
                "trace": [(f"intent_agent[{method}]: {d.intent} category={d.category} months={d.months} "
                           f"also_recommend={d.also_recommend} conf={d.confidence:.2f}")]}

    def authorize(state: State) -> dict:
        role = rbac.get_role(state["role"])
        intent = state["intent"]["intent"]
        if not role.allows(intent):
            return {"outcome": "denied", "answer": f"Your role ({role.name}) is not permitted to run '{intent}' requests. "
                                                    f"Allowed: {', '.join(role.intents)}.",
                    "trace": [f"authorize: DENIED {role.name} -> {intent}"]}
        plan = list(PLANS[intent])
        if intent == "rca" and state["intent"].get("also_recommend") and role.allows("recommendation"):
            plan.append("recommendation_agent")
        return {"plan": plan, "trace": [f"authorize: {role.name} ok -> plan {plan}"]}

    def supervisor(state: State) -> dict:
        return {"step": state.get("step", 0)}

    def next_step(state: State) -> str:
        plan, step = state.get("plan", []), state.get("step", 0)
        return plan[step] if step < len(plan) else "compose"

    def _done(name: str, output: dict, state: State, note: str) -> dict:
        return {"outputs": {name: output}, "step": state.get("step", 0) + 1, "trace": [f"{name}: {note}"]}

    def search_agent(state: State) -> dict:
        out = agents.search(state["question"], state["intent"])
        ids = [h["metadata"]["incident_id"] for h in out["incidents"]]
        return _done("search", out, state, f"{len(ids)} incidents {ids}, {len(out['knowledge'])} knowledge chunks")

    def rca_agent(state: State) -> dict:
        out = agents.rca(state["question"], state["outputs"]["search"])
        return _done("rca", out, state, f"llm={out['llm']}")

    def recommendation_agent(state: State) -> dict:
        out = agents.recommend(state["question"], state["outputs"]["search"], state["outputs"].get("rca"))
        return _done("recommendation", out, state, f"llm={out['llm']} rules={len(out['rules'])}")

    def trend_agent(state: State) -> dict:
        out = agents.trend(state["question"], state["intent"])
        return _done("trend", out, state, f"llm={out['llm']} incidents={out['report'].get('incidents')}")

    def summary_agent(state: State) -> dict:
        style = rbac.get_role(state["role"]).summary_style
        out = agents.summary(state["question"], state["outputs"]["trend"], style)
        return _done("summary", out, state, f"llm={out['llm']} style={style}")

    def compose(state: State) -> dict:
        o = state["outputs"]
        if "summary" in o:
            answer = o["summary"]["answer"]
        elif "rca" in o and "recommendation" in o:
            answer = f"Root cause analysis\n{o['rca']['answer']}\n\nRecommended actions\n{o['recommendation']['answer']}"
        elif "rca" in o:
            answer = o["rca"]["answer"]
        elif "recommendation" in o:
            answer = o["recommendation"]["answer"]
        elif "trend" in o:
            answer = o["trend"]["answer"]
        else:
            answer = o["search"]["answer"]
        citations = sorted({h["metadata"]["incident_id"] for h in o.get("search", {}).get("incidents", [])}
                           | {r["metadata"]["doc_id"] for r in o.get("recommendation", {}).get("rules", [])})
        return {"answer": answer, "citations": citations, "trace": ["compose: done"]}

    def guard_output(state: State) -> dict:
        o = state["outputs"]
        evidence = "\n".join(v.get("evidence", "") + "\n" + v.get("answer", "") * (k == "search")
                             for k, v in o.items()) + "\n" + "\n".join(h["content"] for h in o.get("search", {}).get("incidents", []))
        chk = check_output(state["answer"], evidence, state["question"])
        answer = chk.answer
        if not chk.passed:
            answer += ("\n\nNote: some figures or incident IDs above could not be matched to the source data - "
                       "verify before acting.")
        if not rbac.get_role(state["role"]).can_view_amounts:
            answer = rbac.mask_amounts(answer)
        return {"answer": answer, "outcome": "answered",
                "guardrail": {**state.get("guardrail", {}), "output_issues": chk.issues},
                "trace": [f"guard_output: {chk.issues or 'pass'}"]}

    def finish(state: State) -> dict:
        return {"outcome": state.get("outcome") or "blocked", "citations": [], "trace": ["finish"]}

    g = StateGraph(State)
    for name, fn in [("guard_input", guard_input), ("intent_agent", intent_agent), ("authorize", authorize),
                     ("supervisor", supervisor), ("search_agent", search_agent), ("rca_agent", rca_agent),
                     ("recommendation_agent", recommendation_agent), ("trend_agent", trend_agent),
                     ("summary_agent", summary_agent), ("compose", compose), ("guard_output", guard_output),
                     ("finish", finish)]:
        g.add_node(name, fn)
    g.add_edge(START, "guard_input")
    g.add_conditional_edges("guard_input", lambda st: "finish" if st.get("blocked") else "intent_agent",
                            ["finish", "intent_agent"])
    g.add_edge("intent_agent", "authorize")
    g.add_conditional_edges("authorize", lambda st: "finish" if st.get("outcome") == "denied" else "supervisor",
                            ["finish", "supervisor"])
    agent_nodes = ["search_agent", "rca_agent", "recommendation_agent", "trend_agent", "summary_agent"]
    g.add_conditional_edges("supervisor", next_step, agent_nodes + ["compose"])
    for a in agent_nodes:
        g.add_edge(a, "supervisor")
    g.add_edge("compose", "guard_output")
    g.add_edge("guard_output", END)
    g.add_edge("finish", END)
    return g.compile()


if __name__ == "__main__":
    from unittest.mock import MagicMock

    print(build_graph(llm=MagicMock(), retrievers={}).get_graph().draw_mermaid())
