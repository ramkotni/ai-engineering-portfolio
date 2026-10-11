"""Graph state. `messages` persists across turns (conversation memory via the
checkpointer); every other field is per-turn and reset by the service on each
new question."""
from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

Intent = Literal["policy_question", "claim_status", "greeting", "out_of_scope"]


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    member_id: str | None
    question: str
    standalone_question: str
    search_query: str
    intent: Intent
    claim_id: str | None
    claim: dict | None
    documents: list[dict]
    answer: str
    citations: list[dict]
    grounded: bool | None
    guardrail: dict
    rewrites: int
    regenerations: int
    trace: list[str]


def initial_turn_state(question: str, member_id: str | None, guardrail_flags: list[str]) -> dict:
    return {
        "member_id": member_id,
        "question": question,
        "standalone_question": "",
        "search_query": "",
        "intent": "policy_question",
        "claim_id": None,
        "claim": None,
        "documents": [],
        "answer": "",
        "citations": [],
        "grounded": None,
        "guardrail": {"blocked": False, "reason": None, "flags": list(guardrail_flags)},
        "rewrites": 0,
        "regenerations": 0,
        "trace": [],
    }


# ---- Structured outputs ----------------------------------------------------
class RouteDecision(BaseModel):
    intent: Intent = Field(description="Classified intent")
    standalone_question: str = Field(description="Question rewritten to be self-contained")
    claim_id: str | None = Field(default=None, description="Claim number like CLM-10002 if mentioned")


class GradeResult(BaseModel):
    relevant_ids: list[int] = Field(default_factory=list)


class RewriteResult(BaseModel):
    query: str


class GroundednessResult(BaseModel):
    grounded: bool
    unsupported_claims: list[str] = Field(default_factory=list)
