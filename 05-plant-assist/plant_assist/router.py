"""Question routing: LLM classifier with structured output, deterministic keyword fallback,
and a plant safety policy layered on top of whatever the classifier decides."""

import re
from dataclasses import dataclass
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from plant_assist.llm import structured
from plant_assist.sources import OUT_OF_SCOPE, ROUTE_LABELS, SOURCES

RouteLabel = Literal[ROUTE_LABELS]  # type: ignore[valid-type]


class RouteDecision(BaseModel):
    """Which documentation source(s) should answer the supervisor's question."""

    primary_source: RouteLabel = Field(description="The single best source for the question.")
    secondary_sources: list[RouteLabel] = Field(
        default_factory=list,
        description="Other sources that are also needed for a complete answer (often empty).",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the primary source, 0-1.")
    rationale: str = Field(description="One short sentence explaining the choice.")


@dataclass(frozen=True)
class RetrievalTarget:
    source: str
    query: str
    mandatory: bool = False   # added by policy: keep its best chunk even if similarity is modest
    reason: str = "router"


# --- Safety policy patterns -------------------------------------------------
EMERGENCY_PATTERN = re.compile(
    r"\b(fire|smoke|injur\w*|bleeding|unconscious|trapped|caught in|amputat\w*|burn(ed|t)?|"
    r"chemical (spill|splash|exposure)|spill(ed)?|explosion|electrocut\w*|collapsed?|evacuat\w*)\b",
    re.IGNORECASE,
)
HANDS_ON_TASK_PATTERN = re.compile(
    r"\b(replace|replacing|repair|remove|removing|disassembl\w*|install\w*|change|changing|"
    r"clear(ing)? (a |the )?jam|unjam|bleed|open(ing)? the (cabinet|panel|guard)|adjust\w*|"
    r"rebuild|swap|seal kit|reach(ing)? into)\b",
    re.IGNORECASE,
)
SAFETY_QUERY_PREFIX = "Lockout/tagout, hazardous energy isolation and PPE requirements before: "


def _system_prompt() -> str:
    lines = "\n".join(f"- {s.name}: {s.description}" for s in SOURCES.values())
    return f"""You route questions from manufacturing floor supervisors to the documentation that answers them.

Available sources:
{lines}
- {OUT_OF_SCOPE}: anything unrelated to plant safety, equipment maintenance or quality control (HR, payroll, cafeteria, weather, sports, general trivia, coding).

Rules:
- primary_source is the ONE source most likely to contain the answer.
- Add secondary_sources only when the question genuinely spans domains, e.g. a repair task (maintenance) that also needs lockout/PPE (safety), or a machine problem producing defective parts (maintenance + quality).
- Emergencies, injuries, spills and fires are always primary_source=safety.
- confidence below 0.6 means you are unsure.

Examples:
"How often do I change the filter on the press?" -> maintenance, [], 0.95
"What gloves are required at the parts washer?" -> safety, [], 0.95
"Sample size for a lot of 500 parts?" -> quality, [], 0.9
"Spindle overload alarm keeps coming and parts are out of tolerance" -> maintenance, [quality], 0.75
"Who won the game last night?" -> {OUT_OF_SCOPE}, [], 0.95"""


def llm_route(llm: BaseChatModel, question: str) -> RouteDecision:
    router = structured(llm, RouteDecision)
    decision = router.invoke(
        [SystemMessage(content=_system_prompt()), HumanMessage(content=f"Question: {question}")]
    )
    if decision is None:
        raise ValueError("router returned no structured output")
    return decision


def keyword_route(question: str) -> RouteDecision:
    """Deterministic fallback used when the LLM is unavailable or returns invalid output."""
    q = question.lower()
    hits = {name: sum(kw in q for kw in src.keywords) for name, src in SOURCES.items()}
    ranked = sorted(hits.items(), key=lambda kv: kv[1], reverse=True)
    best, best_hits = ranked[0]
    if best_hits == 0:
        # No vocabulary match: low confidence so the policy searches everything rather than refusing.
        return RouteDecision(
            primary_source=OUT_OF_SCOPE, confidence=0.3, rationale="No domain keywords matched."
        )
    total = sum(hits.values())
    secondary = [name for name, n in ranked[1:] if n > 0 and n >= best_hits / 2]
    return RouteDecision(
        primary_source=best,
        secondary_sources=secondary,
        confidence=round(min(0.9, 0.5 + 0.4 * best_hits / total), 2),
        rationale=f"Keyword match counts: {hits}",
    )


def plan_retrieval(
    decision: RouteDecision, question: str, safety_alert: bool, confidence_threshold: float
) -> list[RetrievalTarget]:
    """Turn the classifier's decision into retrieval targets, applying plant policy:

    1. Low confidence -> search every source (a missed answer is worse than extra context).
    2. Out of scope with high confidence -> no retrieval (polite decline).
    3. Emergency language -> safety is always searched.
    4. Hands-on maintenance work -> safety (LOTO/PPE) is always searched alongside the manual.
    """
    sources: list[str] = []
    for name in [decision.primary_source, *decision.secondary_sources]:
        if name in SOURCES and name not in sources:
            sources.append(name)

    if decision.confidence < confidence_threshold:
        sources += [name for name in SOURCES if name not in sources]
        reason = "low-confidence fan-out"
    elif decision.primary_source == OUT_OF_SCOPE and not safety_alert:
        return []
    else:
        reason = "router"

    targets = [RetrievalTarget(source=name, query=question, reason=reason) for name in sources]

    needs_safety = safety_alert or (
        "maintenance" in sources and HANDS_ON_TASK_PATTERN.search(question) is not None
    )
    if needs_safety:
        why = "emergency language detected" if safety_alert else "hands-on maintenance task"
        if decision.primary_source == "safety":
            # The question is already a safety question; just make sure its best chunk survives grading.
            targets = [
                RetrievalTarget(t.source, t.query, True, f"{t.reason}; {why}") if t.source == "safety" else t
                for t in targets
            ]
        else:
            # Search safety with a LOTO/PPE-focused query so the prerequisites are actually retrieved.
            targets = [t for t in targets if t.source != "safety"]
            targets.append(
                RetrievalTarget("safety", SAFETY_QUERY_PREFIX + question, True, f"policy: {why}")
            )
    return targets
