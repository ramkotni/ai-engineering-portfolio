"""Wires the nodes into a LangGraph StateGraph with conditional routing."""
from __future__ import annotations

import sqlite3

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.config import Settings

from .nodes import AgentNodes, Deps
from .state import AgentState


def make_checkpointer(settings: Settings) -> BaseCheckpointSaver:
    if settings.checkpointer == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver

        return SqliteSaver(sqlite3.connect(str(settings.sqlite_path), check_same_thread=False))
    return InMemorySaver()


def build_graph(deps: Deps, checkpointer: BaseCheckpointSaver | None = None):
    n = AgentNodes(deps)
    s = deps.settings
    g = StateGraph(AgentState)

    g.add_node("input_guard", n.input_guard)
    g.add_node("blocked", n.blocked)
    g.add_node("supervisor", n.supervisor)
    g.add_node("direct_response", n.direct_response)
    g.add_node("claims_agent", n.claims_agent)
    g.add_node("retrieve", n.retrieve)
    g.add_node("grade_documents", n.grade_documents)
    g.add_node("rewrite_query", n.rewrite_query)
    g.add_node("fallback", n.fallback)
    g.add_node("generate", n.generate)
    g.add_node("groundedness_check", n.groundedness_check)
    g.add_node("output_guard", n.output_guard)
    g.add_node("finalize", n.finalize)

    g.add_edge(START, "input_guard")
    g.add_conditional_edges(
        "input_guard", lambda st: "blocked" if st["guardrail"]["blocked"] else "supervisor",
        {"blocked": "blocked", "supervisor": "supervisor"},
    )
    g.add_edge("blocked", "finalize")

    g.add_conditional_edges(
        "supervisor",
        lambda st: st["intent"],
        {
            "policy_question": "retrieve",
            "claim_status": "claims_agent",
            "greeting": "direct_response",
            "out_of_scope": "direct_response",
        },
    )
    g.add_edge("direct_response", "output_guard")

    def after_claims(st: AgentState) -> str:
        if st.get("answer"):  # agent already answered (not found / need claim id / list)
            return "output_guard"
        return "retrieve" if (st.get("claim") or {}).get("denial_code") else "generate"

    g.add_conditional_edges("claims_agent", after_claims, {"output_guard": "output_guard", "retrieve": "retrieve", "generate": "generate"})

    g.add_edge("retrieve", "grade_documents")

    def after_grading(st: AgentState) -> str:
        if st.get("documents"):
            return "generate"
        if st.get("rewrites", 0) < s.max_query_rewrites:
            return "rewrite_query"
        return "generate" if st.get("claim") else "fallback"

    g.add_conditional_edges("grade_documents", after_grading, {"generate": "generate", "rewrite_query": "rewrite_query", "fallback": "fallback"})
    g.add_edge("rewrite_query", "retrieve")
    g.add_edge("fallback", "output_guard")

    g.add_edge("generate", "groundedness_check")

    def after_groundedness(st: AgentState) -> str:
        if st.get("grounded") is False and st.get("regenerations", 0) <= s.max_regenerations:
            return "generate"
        return "output_guard"

    g.add_conditional_edges("groundedness_check", after_groundedness, {"generate": "generate", "output_guard": "output_guard"})
    g.add_edge("output_guard", "finalize")
    g.add_edge("finalize", END)

    return g.compile(checkpointer=checkpointer)
