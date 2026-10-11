r"""LangGraph wiring for PlantAssist.

    START -> analyze_query (input guardrails) -> route_question --(Send fan-out)--> retrieve x N -> grade_documents
          grade_documents -> generate -> check_grounding -> finalize -> END
                          \-> rewrite_query -> route_question   (corrective retrieval loop)
                          \-> no_answer -> END                   (escalate, never guess)
          analyze_query   -> guardrail_block -> END             (unsafe request / prompt injection)
          route_question  -> out_of_scope -> END
          check_grounding -> generate                            (regenerate once if ungrounded)

Run `python -m plant_assist.graph` to print the Mermaid diagram.
"""

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph

from plant_assist.config import Settings, get_settings
from plant_assist.nodes import PlantAssistNodes
from plant_assist.retrieval import SourceRetriever
from plant_assist.state import GraphState


def build_graph(
    llm: BaseChatModel | None = None,
    retrievers: dict[str, SourceRetriever] | None = None,
    settings: Settings | None = None,
):
    if llm is None:
        from plant_assist.llm import get_chat_model

        llm = get_chat_model()
    if retrievers is None:
        from plant_assist.retrieval import get_retrievers

        retrievers = get_retrievers()
    n = PlantAssistNodes(llm, retrievers, settings or get_settings())

    g = StateGraph(GraphState)
    g.add_node("analyze_query", n.analyze_query)
    g.add_node("route_question", n.route_question)
    g.add_node("retrieve", n.retrieve)
    g.add_node("grade_documents", n.grade_documents)
    g.add_node("rewrite_query", n.rewrite_query)
    g.add_node("generate", n.generate)
    g.add_node("check_grounding", n.check_grounding)
    g.add_node("finalize", n.finalize)
    g.add_node("no_answer", n.no_answer)
    g.add_node("out_of_scope", n.out_of_scope)
    g.add_node("access_denied", n.access_denied)
    g.add_node("guardrail_block", n.guardrail_block)

    g.add_edge(START, "analyze_query")
    g.add_conditional_edges("analyze_query", n.decide_after_analysis, ["route_question", "guardrail_block"])
    g.add_conditional_edges("route_question", n.dispatch, ["retrieve", "out_of_scope", "access_denied"])
    g.add_edge("retrieve", "grade_documents")
    g.add_conditional_edges(
        "grade_documents", n.decide_after_grading, ["generate", "rewrite_query", "no_answer"]
    )
    g.add_edge("rewrite_query", "route_question")
    g.add_edge("generate", "check_grounding")
    g.add_conditional_edges("check_grounding", n.decide_after_grounding, ["generate", "finalize"])
    g.add_edge("finalize", END)
    g.add_edge("no_answer", END)
    g.add_edge("out_of_scope", END)
    g.add_edge("guardrail_block", END)
    g.add_edge("access_denied", END)
    return g.compile()


if __name__ == "__main__":
    from unittest.mock import MagicMock

    # Only the structure is needed to draw the diagram - no model or index required.
    print(build_graph(llm=MagicMock(), retrievers={}).get_graph().draw_mermaid())
