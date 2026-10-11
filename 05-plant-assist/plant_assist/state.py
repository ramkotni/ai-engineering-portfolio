"""LangGraph state for the PlantAssist workflow."""

import operator
from typing import Annotated, TypedDict


def merge_documents(left: list[dict] | None, right: list[dict] | None) -> list[dict]:
    """Reducer for parallel retrievers: concatenates fan-in results; `None` resets (used on query rewrite)."""
    if right is None:
        return []
    return (left or []) + right


class GraphState(TypedDict, total=False):
    question: str                 # original supervisor question
    role: str                     # caller's role (roles.yaml)
    restricted_sources: list[str] # sources the router wanted but the role may not search
    search_query: str             # possibly rewritten query used for routing + retrieval
    safety_alert: bool            # emergency language detected
    blocked: bool                 # input guardrail refused the request
    guardrail: dict               # input category/flags + output issues (audit and UI)
    route: dict                   # RouteDecision + method (llm | keyword-fallback)
    targets: list[dict]           # RetrievalTarget(s) chosen by router + policy
    documents: Annotated[list[dict], merge_documents]  # raw hits from all retrievers
    context: list[dict]           # graded, de-duplicated chunks passed to the generator
    answer: str
    citations: list[dict]
    grounded: bool | None
    unsupported_claims: list[str]
    rewrite_count: int
    generation_attempts: int
    outcome: str                  # answered | no_answer | out_of_scope | blocked | denied
    trace: Annotated[list[str], operator.add]


class RetrieveTask(TypedDict):
    """Payload sent to each parallel `retrieve` branch via LangGraph `Send`."""

    source: str
    query: str
    mandatory: bool
    reason: str
