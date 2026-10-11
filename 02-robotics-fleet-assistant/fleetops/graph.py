r"""Multi-agent LangGraph (supervisor pattern).

  START -> guard_input --blocked--> finish
          intent_agent -> authorize (role intents + zone scope) --denied--> finish
          supervisor <-> fleet_search | diagnostics | battery | maintenance | fleet_status | task_optimization | summary
          compose -> guard_output -> END
"""

import operator
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from fleetops import rbac
from fleetops.agents import FleetAgents
from fleetops.config import Settings, get_settings
from fleetops.data import table
from fleetops.guardrails import check_input, check_output


def merge(a: dict | None, b: dict | None) -> dict:
    return {**(a or {}), **(b or {})}


class State(TypedDict, total=False):
    question: str
    role: str
    blocked: bool
    guardrail: dict
    intent: dict
    zones: list[str]
    plan: list[str]
    step: int
    outputs: Annotated[dict, merge]
    answer: str
    citations: list[str]
    outcome: str
    trace: Annotated[list[str], operator.add]


PLANS = {
    "robot_diagnostics": ["fleet_search", "diagnostics"],
    "navigation_issues": ["fleet_search", "diagnostics"],
    "battery_analysis": ["battery"],
    "predictive_maintenance": ["battery", "maintenance"],
    "task_assignment": ["fleet_status", "task_optimization"],
    "fleet_status": ["fleet_status"],
    "operational_summary": ["fleet_status", "battery", "maintenance", "summary"],
}
AGENT_NODES = ["fleet_search", "diagnostics", "battery", "maintenance", "fleet_status", "task_optimization", "summary"]


def build_graph(llm: BaseChatModel | None = None, retrievers: dict | None = None, settings: Settings | None = None):
    s = settings or get_settings()
    if llm is None:
        from fleetops.llm import get_chat_model

        llm = get_chat_model()
    if retrievers is None:
        from fleetops.retrieval import get_retrievers

        retrievers = get_retrievers()
    agents = FleetAgents(llm, retrievers, s)

    def guard_input(state: State) -> dict:
        chk = check_input(state["question"], s.max_question_chars)
        return {"question": chk.question, "blocked": not chk.allowed, "answer": chk.message or "", "step": 0,
                "guardrail": {"input_category": chk.category, "input_flags": chk.flags},
                "trace": [f"guard_input: {chk.category or 'pass'}"]}

    def intent_agent(state: State) -> dict:
        d, method = agents.classify(state["question"])
        if d.intent == "navigation_issues" and d.event_type is None:
            d.event_type = "navigation_exception"
        return {"intent": {**d.model_dump(), "method": method},
                "trace": [f"intent_agent[{method}]: {d.intent} robot={d.robot_id} zone={d.zone} event={d.event_type}"]}

    def authorize(state: State) -> dict:
        role = rbac.get_role(state["role"])
        intent = state["intent"]
        if not role.allows(intent["intent"]):
            return {"outcome": "denied", "answer": f"Your role ({role.name}) is not permitted to run '{intent['intent']}'. "
                                                    f"Allowed: {', '.join(role.intents)}.",
                    "trace": [f"authorize: DENIED intent {intent['intent']}"]}
        robots = table("robots")
        if intent.get("robot_id"):
            row = robots[robots.robot_id == intent["robot_id"]]
            if row.empty:
                return {"outcome": "denied", "answer": f"Robot {intent['robot_id']} is not in the fleet register.",
                        "trace": ["authorize: unknown robot"]}
            if not role.can_see_zone(row.iloc[0].zone):
                return {"outcome": "denied", "answer": f"Robot {intent['robot_id']} is in {row.iloc[0].zone}, outside your zones "
                                                        f"({', '.join(role.zones)}).", "trace": ["authorize: DENIED zone"]}
        zones = list(role.zones)
        if intent.get("zone"):
            zones = [intent["zone"]] if role.can_see_zone(intent["zone"]) else zones
        return {"plan": list(PLANS[intent["intent"]]), "zones": zones,
                "trace": [f"authorize: {role.name} ok, zones={zones or 'all'} plan={PLANS[intent['intent']]}"]}

    def supervisor(state: State) -> dict:
        return {"step": state.get("step", 0)}

    def next_step(state: State) -> str:
        plan, step = state.get("plan", []), state.get("step", 0)
        return plan[step] if step < len(plan) else "compose"

    def is_final(state: State) -> bool:
        return state.get("step", 0) == len(state.get("plan", [])) - 1

    def done(name: str, out: dict, state: State) -> dict:
        return {"outputs": {name: out}, "step": state.get("step", 0) + 1, "trace": [f"{name}: llm={out.get('llm')}"]}

    def fleet_search(state: State) -> dict:
        out = agents.search(state["question"], state["intent"], state.get("zones", []))
        return {**done("fleet_search", out, state), "trace": [f"fleet_search: {[h['id'] for h in out['events']]}"]}

    def diagnostics(state: State) -> dict:
        return done("diagnostics", agents.diagnostics(state["question"], state["intent"], state["outputs"]["fleet_search"],
                                                      is_final(state)), state)

    def battery(state: State) -> dict:
        return done("battery", agents.battery(state["question"], state["intent"], state.get("zones", []), is_final(state)), state)

    def maintenance(state: State) -> dict:
        return done("maintenance", agents.maintenance(state["question"], state.get("zones", []),
                                                      state.get("outputs", {}).get("battery"), is_final(state)), state)

    def fleet_status(state: State) -> dict:
        return done("fleet_status", agents.fleet_status(state.get("zones", [])), state)

    def task_optimization(state: State) -> dict:
        return done("task_optimization", agents.task_optimization(state["question"], state.get("zones", []), is_final(state)), state)

    def summary(state: State) -> dict:
        style = rbac.get_role(state["role"]).summary_style
        return done("summary", agents.summary(state["question"], state["outputs"], state.get("zones", []), style), state)

    def compose(state: State) -> dict:
        last = state["plan"][-1]
        o = state["outputs"]
        cites = sorted({h["id"] for h in o.get("fleet_search", {}).get("events", [])}
                       | {g["metadata"]["doc_id"] for g in o.get("fleet_search", {}).get("guide", [])})
        return {"answer": o[last]["answer"], "citations": cites, "trace": ["compose"]}

    def guard_output(state: State) -> dict:
        evidence = "\n".join(v.get("evidence", "") + "\n" + v.get("answer", "") * (not v.get("llm"))
                             for v in state["outputs"].values())
        chk = check_output(state["answer"], evidence, state["question"])
        answer = chk.answer
        if "unsafe_advice" in chk.issues:
            answer = "I can't provide that answer safely. Follow RB-GUIDE-001 'Safety Before Any Work' and contact the maintenance lead."
        elif not chk.passed:
            answer += "\n\nNote: some figures or IDs above could not be matched to fleet data - verify before acting."
        return {"answer": answer, "outcome": "answered", "guardrail": {**state.get("guardrail", {}), "output_issues": chk.issues},
                "trace": [f"guard_output: {chk.issues or 'pass'}"]}

    def finish(state: State) -> dict:
        return {"outcome": state.get("outcome") or "blocked", "citations": [], "trace": ["finish"]}

    g = StateGraph(State)
    nodes = {"guard_input": guard_input, "intent_agent": intent_agent, "authorize": authorize, "supervisor": supervisor,
             "fleet_search": fleet_search, "diagnostics": diagnostics, "battery": battery, "maintenance": maintenance,
             "fleet_status": fleet_status, "task_optimization": task_optimization, "summary": summary,
             "compose": compose, "guard_output": guard_output, "finish": finish}
    for name, fn in nodes.items():
        g.add_node(name, fn)
    g.add_edge(START, "guard_input")
    g.add_conditional_edges("guard_input", lambda st: "finish" if st.get("blocked") else "intent_agent", ["finish", "intent_agent"])
    g.add_edge("intent_agent", "authorize")
    g.add_conditional_edges("authorize", lambda st: "finish" if st.get("outcome") == "denied" else "supervisor",
                            ["finish", "supervisor"])
    g.add_conditional_edges("supervisor", next_step, AGENT_NODES + ["compose"])
    for a in AGENT_NODES:
        g.add_edge(a, "supervisor")
    g.add_edge("compose", "guard_output")
    g.add_edge("guard_output", END)
    g.add_edge("finish", END)
    return g.compile()
