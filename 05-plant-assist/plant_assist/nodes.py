"""Node implementations for the PlantAssist LangGraph workflow.

Dependencies (chat model, retrievers, settings) are injected so the graph can be tested
with fakes and run against Ollama locally or Bedrock in AWS without code changes.
"""

import logging
from dataclasses import asdict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import Send
from pydantic import BaseModel, Field

from plant_assist import rbac
from plant_assist.config import Settings
from plant_assist.guardrails import check_input, check_output
from plant_assist.llm import structured
from plant_assist.retrieval import SourceRetriever
from plant_assist.router import (
    EMERGENCY_PATTERN,
    keyword_route,
    llm_route,
    plan_retrieval,
)
from plant_assist.sources import SOURCES
from plant_assist.state import GraphState, RetrieveTask

log = logging.getLogger(__name__)

# Deterministic text: plant policy, never left to the LLM.
EMERGENCY_BANNER = (
    "SAFETY ALERT: If anyone is hurt or in immediate danger, stop work and call plant "
    "emergency ext. 5555 (mobile 555-0100) or 911 now. Do not wait for this answer."
)

ANSWER_SYSTEM_PROMPT = """You are PlantAssist, a documentation assistant for manufacturing floor supervisors.
Answer ONLY from the numbered documentation excerpts provided.

Rules:
- Use only the excerpts that are relevant to the question and ignore the rest.
- Do not add general advice, PPE, or steps that are not written in the excerpts.
- Cite the excerpt number in brackets after each fact, e.g. "Torque to 210 ft-lb [2]."
- Never invent values (torques, pressures, limits, intervals, part numbers). If the excerpts do not contain the answer, say "The documentation does not cover this" and stop.
- Be concise and actionable: short intro sentence, then numbered steps or bullets. No preamble about being an AI.
- Copy numbers and units exactly as written in the excerpts.
{guidance}"""

GROUNDING_PROMPT = """You verify answers produced from plant documentation.
Decide whether every factual claim in the ANSWER (numbers, steps, requirements, contacts) is supported by the EXCERPTS.
Statements that the documentation does not cover something count as supported.
Return grounded=false only if the answer states a fact that is missing from or contradicts the excerpts, and list those claims."""

REWRITE_PROMPT = """Rewrite the supervisor's question so it is easier to search in plant documentation
(safety procedures, equipment maintenance manuals, quality control standards).
Expand abbreviations, use precise technical terms, keep equipment IDs (e.g. HP-200, VMC-500) unchanged.
Return ONLY the rewritten question."""


class GroundingVerdict(BaseModel):
    grounded: bool = Field(description="True if every factual claim is supported by the excerpts.")
    unsupported_claims: list[str] = Field(default_factory=list)


class PlantAssistNodes:
    def __init__(self, llm: BaseChatModel, retrievers: dict[str, SourceRetriever], settings: Settings):
        self.llm = llm
        self.retrievers = retrievers
        self.s = settings

    # ------------------------------------------------------------------ 1. input guardrails
    def analyze_query(self, state: GraphState) -> dict:
        check = check_input(state["question"], self.s.max_question_chars)
        question = check.question  # normalised + PII-redacted before any LLM sees it
        alert = EMERGENCY_PATTERN.search(question) is not None
        return {
            "question": question,
            "search_query": question,
            "safety_alert": alert,
            "blocked": not check.allowed,
            "guardrail": {"input_category": check.category, "input_flags": check.flags},
            "answer": check.message or "",
            "rewrite_count": 0,
            "generation_attempts": 0,
            "documents": None,
            "trace": [f"analyze_query: safety_alert={alert} input_guardrail={check.category or 'pass'} flags={check.flags}"],
        }

    @staticmethod
    def decide_after_analysis(state: GraphState) -> str:
        return "guardrail_block" if state.get("blocked") else "route_question"

    # ------------------------------------------------------------------ 2. routing
    def route_question(self, state: GraphState) -> dict:
        query = state["search_query"]
        try:
            decision, method = llm_route(self.llm, query), "llm"
        except Exception as exc:  # noqa: BLE001 - model down, invalid JSON, schema violation
            log.warning("LLM router failed (%s); using keyword fallback", exc)
            decision, method = keyword_route(query), "keyword-fallback"

        targets = plan_retrieval(
            decision, query, state.get("safety_alert", False), self.s.route_confidence_threshold
        )
        # Role-based access: drop sources the caller may not search (safety is always allowed).
        role = rbac.get_role(state.get("role") or self.s.default_role)
        restricted = sorted({t.source for t in targets if not role.can_search(t.source)})
        targets = [t for t in targets if role.can_search(t.source)]
        summary = ", ".join(f"{t.source}{'*' if t.mandatory else ''}" for t in targets) or "none"
        return {
            "route": {**decision.model_dump(), "method": method},
            "targets": [asdict(t) for t in targets],
            "restricted_sources": restricted,
            "trace": [
                (
                    f"route_question[{method}]: primary={decision.primary_source} "
                    f"secondary={decision.secondary_sources} conf={decision.confidence:.2f} -> search [{summary}]"
                )
            ],
        }

    @staticmethod
    def dispatch(state: GraphState) -> list[Send] | str:
        """Conditional edge: fan out one parallel `retrieve` branch per target source."""
        targets = state.get("targets") or []
        if not targets and state.get("restricted_sources"):
            return "access_denied"
        if not targets:
            return "out_of_scope"
        return [Send("retrieve", RetrieveTask(**t)) for t in targets]

    # ------------------------------------------------------------------ 3. retrieval (parallel)
    def retrieve(self, task: RetrieveTask) -> dict:
        k = self.s.policy_top_k if task["reason"].startswith("policy") else self.s.top_k
        hits = self.retrievers[task["source"]].search(task["query"], k)
        for h in hits:
            h["mandatory"] = task["mandatory"]
        best = max((h["score"] for h in hits), default=0.0)
        return {
            "documents": hits,
            "trace": [f"retrieve[{task['source']}]: {len(hits)} chunks, best cosine={best:.2f} ({task['reason']})"],
        }

    # ------------------------------------------------------------------ 4. grading
    def grade_documents(self, state: GraphState) -> dict:
        unique: dict[tuple, dict] = {}
        for d in state.get("documents") or []:
            key = (d["doc_id"], d["content"])
            if key not in unique or d["rrf"] > unique[key]["rrf"]:
                unique[key] = d
        docs = list(unique.values())

        relevant = [d for d in docs if d["score"] >= self.s.min_relevance]
        # Policy-mandated sources (e.g. LOTO for hands-on work) keep their best chunk.
        for source in {d["source"] for d in docs if d.get("mandatory")}:
            if not any(d["source"] == source for d in relevant):
                relevant.append(max((d for d in docs if d["source"] == source), key=lambda d: d["rrf"]))

        # Interleave sources (in routing order) so one source cannot crowd out another.
        order = [t["source"] for t in state.get("targets", [])]
        by_source = {
            s: sorted((d for d in relevant if d["source"] == s), key=lambda d: d["rrf"], reverse=True)
            for s in order
        }
        context: list[dict] = []
        for rank in range(self.s.top_k):
            for s in order:
                if rank < len(by_source.get(s, [])) and len(context) < self.s.max_context_chunks:
                    context.append(by_source[s][rank])

        return {
            "context": context,
            "trace": [f"grade_documents: {len(docs)} retrieved -> {len(relevant)} relevant -> {len(context)} in context"],
        }

    def decide_after_grading(self, state: GraphState) -> str:
        if state.get("context"):
            return "generate"
        if state.get("rewrite_count", 0) < self.s.max_query_rewrites:
            return "rewrite_query"
        return "no_answer"

    # ------------------------------------------------------------------ 5. corrective loop
    def rewrite_query(self, state: GraphState) -> dict:
        try:
            msg = self.llm.invoke(
                [SystemMessage(content=REWRITE_PROMPT), HumanMessage(content=state["question"])]
            )
            new_query = str(msg.content).strip().strip('"') or state["search_query"]
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the request
            log.warning("Query rewrite failed: %s", exc)
            new_query = state["search_query"]
        return {
            "search_query": new_query,
            "rewrite_count": state.get("rewrite_count", 0) + 1,
            "documents": None,  # reset fan-in accumulator before re-routing
            "trace": [f"rewrite_query: '{new_query}'"],
        }

    # ------------------------------------------------------------------ 6. generation
    def generate(self, state: GraphState) -> dict:
        context = state["context"]
        sources_used = list(dict.fromkeys(c["source"] for c in context))
        guidance = "\n".join(
            f"- {SOURCES[s].display_name}: {SOURCES[s].answer_guidance}" for s in sources_used
        )
        excerpts = "\n\n".join(
            f"[{i}] {c['title']} ({c['doc_id']} rev {c['revision']}) - {c['section']}\n"
            f"{c['content'].split(chr(10), 1)[-1]}"
            for i, c in enumerate(context, start=1)
        )
        user = f"Question: {state['question']}\n\nDocumentation excerpts:\n{excerpts}"
        if state.get("grounded") is False:
            claims = "; ".join(state.get("unsupported_claims") or []) or "see previous answer"
            user += (
                "\n\nA reviewer found unsupported claims in your previous answer: "
                f"{claims}. Answer again using only facts stated in the excerpts."
            )

        msg = self.llm.invoke(
            [SystemMessage(content=ANSWER_SYSTEM_PROMPT.format(guidance=guidance)), HumanMessage(content=user)]
        )
        citations = [
            {
                "ref": i,
                "source": c["source"],
                "doc_id": c["doc_id"],
                "title": c["title"],
                "section": c["section"],
                "section_path": c.get("section_path", ""),
                "content_type": c.get("content_type", "text"),
                "revision": c["revision"],
                "score": c["score"],
            }
            for i, c in enumerate(context, start=1)
        ]
        attempts = state.get("generation_attempts", 0) + 1
        return {
            "answer": str(msg.content).strip(),
            "citations": citations,
            "generation_attempts": attempts,
            "trace": [f"generate: attempt {attempts} using {len(context)} excerpts from {sources_used}"],
        }

    # ------------------------------------------------------------------ 7. output guardrails + hallucination check
    def check_grounding(self, state: GraphState) -> dict:
        # (a) Deterministic output guardrails - always on, no model needed.
        texts = [c["content"] for c in state["context"]]
        out = check_output(state["answer"], texts, state["question"])
        unsupported = []
        if self.s.numeric_grounding_check:
            unsupported += [f"the number {n} does not appear in the documentation" for n in out.unsupported_numbers]
        if out.unsafe_advice:
            unsupported.append("the answer suggests defeating a safety protection")
        guardrail = {**state.get("guardrail", {}), "output_issues": out.issues}
        if unsupported:
            return {
                "answer": out.answer,
                "grounded": False,
                "unsupported_claims": unsupported,
                "guardrail": guardrail,
                "trace": [f"check_grounding[rules]: failed {out.issues}"],
            }

        # (b) LLM verifier - optional second pass for claims rules cannot see (steps, requirements).
        if not self.s.grounding_check:
            return {
                "answer": out.answer,
                "grounded": None,
                "guardrail": guardrail,
                "trace": [f"check_grounding[rules]: passed {out.issues}; LLM check disabled"],
            }
        excerpts = "\n\n".join(f"[{i}] {t}" for i, t in enumerate(texts, start=1))
        try:
            verdict: GroundingVerdict = structured(self.llm, GroundingVerdict).invoke(
                [
                    SystemMessage(content=GROUNDING_PROMPT),
                    HumanMessage(content=f"EXCERPTS:\n{excerpts}\n\nANSWER:\n{out.answer}"),
                ]
            )
            if verdict is None:
                raise ValueError("no verdict")
        except Exception as exc:  # noqa: BLE001 - degrade gracefully, never crash the request
            log.warning("Grounding check unavailable: %s", exc)
            return {
                "answer": out.answer,
                "grounded": None,
                "guardrail": guardrail,
                "trace": ["check_grounding[llm]: unavailable (answer not verified)"],
            }
        return {
            "answer": out.answer,
            "grounded": verdict.grounded,
            "unsupported_claims": verdict.unsupported_claims,
            "guardrail": guardrail,
            "trace": [f"check_grounding[llm]: grounded={verdict.grounded} unsupported={verdict.unsupported_claims}"],
        }

    def decide_after_grounding(self, state: GraphState) -> str:
        if state.get("grounded") is False and state.get("generation_attempts", 0) < self.s.max_generation_attempts:
            return "generate"
        return "finalize"

    # ------------------------------------------------------------------ 8. terminal nodes
    def finalize(self, state: GraphState) -> dict:
        answer = state["answer"]
        if "unsafe_advice" in state.get("guardrail", {}).get("output_issues", []):
            # Never show an answer that tells a supervisor to defeat a protection.
            return {
                "answer": (
                    "I can't provide that answer safely. Follow SOP-SAF-001 (lockout/tagout) and SOP-SAF-003 "
                    "(PPE), and contact the EHS Manager (ext. 4400) before proceeding."
                ),
                "citations": [],
                "outcome": "blocked",
                "trace": ["finalize: unsafe answer withheld"],
            }
        if state.get("grounded") is False:
            answer += (
                "\n\nNote: parts of this answer could not be verified against the documentation. "
                "Confirm with the document owner before acting."
            )
        if state.get("restricted_sources"):
            names = ", ".join(SOURCES[s].display_name for s in state["restricted_sources"])
            answer += f"\n\nNote: {names} are not available for your role, so this answer may be incomplete."
        if state.get("safety_alert"):
            answer = f"{EMERGENCY_BANNER}\n\n{answer}"
        return {"answer": answer, "outcome": "answered", "trace": ["finalize: answered"]}

    def access_denied(self, state: GraphState) -> dict:
        names = ", ".join(SOURCES[s].display_name for s in state.get("restricted_sources", []))
        role = state.get("role") or self.s.default_role
        return {"answer": f"Your role ({role}) cannot search {names}. Ask a colleague with access or the document owner.",
                "citations": [], "outcome": "denied", "trace": ["access_denied"]}

    def no_answer(self, state: GraphState) -> dict:
        searched = list(dict.fromkeys(t["source"] for t in state.get("targets", []))) or list(SOURCES)
        names = ", ".join(SOURCES[s].display_name for s in searched)
        contacts = "; ".join(f"{SOURCES[s].display_name}: {SOURCES[s].escalation}" for s in searched)
        answer = (
            f"I could not find this in the {names} documentation, so I won't guess. "
            f"Please contact - {contacts}."
        )
        if state.get("safety_alert"):
            answer = f"{EMERGENCY_BANNER}\n\n{answer}"
        return {"answer": answer, "citations": [], "outcome": "no_answer", "trace": ["no_answer: escalated"]}

    def guardrail_block(self, state: GraphState) -> dict:
        return {
            "citations": [],
            "outcome": "blocked",
            "trace": [f"guardrail_block: {state.get('guardrail', {}).get('input_category')}"],
        }

    def out_of_scope(self, state: GraphState) -> dict:
        covered = ", ".join(s.display_name for s in SOURCES.values())
        return {
            "answer": (
                "That question is outside what I can answer. I cover plant documentation only: "
                f"{covered}. Please rephrase if your question relates to one of these."
            ),
            "citations": [],
            "outcome": "out_of_scope",
            "trace": ["out_of_scope: declined"],
        }
