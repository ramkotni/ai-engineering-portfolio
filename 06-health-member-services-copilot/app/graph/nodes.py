"""LangGraph nodes. Each node is a small, single-purpose "agent" or step.

  input_guard -> supervisor -> {policy RAG agent | claims agent | direct reply}
  policy RAG agent = retrieve -> grade -> (rewrite -> retrieve)* -> generate
  critic           = groundedness_check -> (regenerate)* -> output_guard
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel

from app import prompts
from app.config import Settings
from app.guardrails import BLOCKED_MESSAGE, Guardrails
from app.tools import ClaimsRepository, extract_claim_id
from app.vectorstore import KnowledgeBase

from .state import AgentState, GradeResult, GroundednessResult, RewriteResult, RouteDecision

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


@dataclass
class Deps:
    llm: BaseChatModel
    kb: KnowledgeBase
    claims: ClaimsRepository
    guardrails: Guardrails
    settings: Settings


def _extract_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in model output")
    return json.loads(text[start : end + 1])


def invoke_structured(llm: BaseChatModel, schema: type[T], messages: list, default: T) -> T:
    """Structured output with graceful degradation.

    1) native structured output (Ollama JSON-schema / Bedrock tool-use)
    2) plain completion + JSON extraction
    3) safe default  -> the graph never crashes on a malformed LLM response
    """
    try:
        result = llm.with_structured_output(schema).invoke(messages)
        if isinstance(result, schema):
            return result
        if isinstance(result, dict):
            return schema.model_validate(result)
    except Exception as exc:  # noqa: BLE001
        logger.debug("structured output failed (%s), falling back to text parsing", exc)
    try:
        raw = llm.invoke(messages).content
        return schema.model_validate(_extract_json(raw if isinstance(raw, str) else str(raw)))
    except Exception as exc:  # noqa: BLE001
        logger.warning("structured parse failed for %s: %s", schema.__name__, exc)
        return default


_MONEY_PCT_RE = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)|(\d+(?:\.\d+)?)\s?%")
_JSON_AMOUNT_RE = re.compile(r":\s*(\d+\.\d+)")  # claim-record amounts, e.g. "plan_paid": 1700.0
_DURATION_RE = re.compile(r"\b(\d+)\s*(?:calendar\s+|business\s+)?(?:days?|months?|hours?|years?)\b", re.IGNORECASE)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def unsupported_numbers(answer: str, context: str) -> list[str]:
    """Dollar amounts, percentages and time limits in the answer that do not appear in the context.
    Type-aware: "$25" is NOT supported by "25%"; "120 days" needs a 120-day/month/hour limit in context."""
    money, pct = set(), set()
    for m in _MONEY_PCT_RE.finditer(context):
        (money if m.group(1) else pct).add(_num(m.group(1) or m.group(2)))
    money |= {_num(v) for v in _JSON_AMOUNT_RE.findall(context)}
    bad = []
    for m in _MONEY_PCT_RE.finditer(answer):
        is_money = m.group(1) is not None
        value = _num(m.group(1) if is_money else m.group(2))
        if value not in (money if is_money else pct):
            bad.append(m.group(0).strip())
    durations = {int(n) for n in _DURATION_RE.findall(context)}
    bad += [m.group(0) for m in _DURATION_RE.finditer(answer) if int(m.group(1)) not in durations]
    return bad


_INSURANCE_TERMS = re.compile(
    r"\b(claims?|copays?|deductibles?|coinsurance|cover(ed|age)?|plan|benefits?|appeals?|prior auth\w*|pharmacy|"
    r"formulary|premiums?|in-network|out-of-network|referral|enroll\w*|id card|eob|reimburse\w*)\b",
    re.IGNORECASE,
)


def claim_summary(claim: dict) -> str:
    """Deterministic, always-correct claim facts (the LLM adds explanation after)."""
    parts = [f"Claim {claim['claim_id']} ({claim['service']}, {claim['service_date']}): {claim['status']} [CLAIM]."]
    if claim.get("member_responsibility") is not None:
        parts.append(f"Your responsibility: ${claim['member_responsibility']:,.2f}.")
    if claim.get("denial_reason"):
        parts.append(f"Reason ({claim['denial_code']}): {claim['denial_reason']}")
    return " ".join(parts)


def _format_history(state: AgentState, window: int) -> str:
    history = state.get("messages", [])[:-1][-window:]
    lines = []
    for m in history:
        role = "Member" if isinstance(m, HumanMessage) else "Assistant"
        lines.append(f"{role}: {m.content}")
    return "\n".join(lines) or "(no prior conversation)"


def _build_context(state: AgentState) -> str:
    parts = []
    claim = state.get("claim")
    if claim:
        parts.append("[CLAIM] Member claim record:\n" + json.dumps(claim, indent=2))
    for i, d in enumerate(state.get("documents", []), start=1):
        parts.append(f"[{i}] (source: {d['source']})\n{d['content']}")
    return "\n\n".join(parts)


class AgentNodes:
    def __init__(self, deps: Deps):
        self.d = deps
        self.s = deps.settings

    # ------------------------------------------------------------ guards ---
    def input_guard(self, state: AgentState) -> dict:
        question = state["question"]
        result = self.d.guardrails.check_input(question)
        guard = dict(state.get("guardrail") or {})
        guard["flags"] = list(guard.get("flags", [])) + result.flags
        guard["blocked"] = result.blocked
        guard["reason"] = result.reason
        return {
            "messages": [HumanMessage(content=question)],
            "guardrail": guard,
            "trace": state.get("trace", []) + ["input_guard" + (":blocked" if result.blocked else "")],
        }

    def blocked(self, state: AgentState) -> dict:
        return {"answer": BLOCKED_MESSAGE, "intent": "out_of_scope", "trace": state["trace"] + ["blocked"]}

    # -------------------------------------------------------- supervisor ---
    def supervisor(self, state: AgentState) -> dict:
        question = state["question"]
        history = _format_history(state, self.s.history_window)
        decision = invoke_structured(
            self.d.llm,
            RouteDecision,
            [
                SystemMessage(content=prompts.SUPERVISOR_SYSTEM),
                HumanMessage(content=f"Conversation so far:\n{history}\n\nLatest member message: {question}"),
            ],
            default=RouteDecision(intent="policy_question", standalone_question=question),
        )
        # Deterministic signals override the LLM where they are unambiguous.
        claim_id = extract_claim_id(question) or extract_claim_id(decision.claim_id or "")
        intent = decision.intent
        if claim_id and intent in ("policy_question", "out_of_scope"):
            intent = "claim_status"
        elif intent == "out_of_scope" and _INSURANCE_TERMS.search(question):
            intent = "policy_question"  # don't refuse insurance questions; retrieval decides
        standalone = decision.standalone_question.strip() or question
        return {
            "intent": intent,
            "claim_id": claim_id,
            "standalone_question": standalone,
            "search_query": standalone,
            "trace": state["trace"] + [f"supervisor:{intent}"],
        }

    def direct_response(self, state: AgentState) -> dict:
        answer = prompts.GREETING_REPLY if state["intent"] == "greeting" else prompts.OUT_OF_SCOPE_REPLY
        return {"answer": answer, "grounded": None, "trace": state["trace"] + ["direct_response"]}

    # ------------------------------------------------------ claims agent ---
    def claims_agent(self, state: AgentState) -> dict:
        claim_id = state.get("claim_id")
        member_id = state.get("member_id")
        trace = state["trace"]
        if not claim_id:
            claims = self.d.claims.list_claims(member_id) if member_id else []
            if not claims:
                return {"answer": "Which claim would you like to check? Please share the claim number (for example CLM-10001).",
                        "trace": trace + ["claims_agent:need_claim_id"]}
            listing = "\n".join(f"- {c['claim_id']}: {c['service']} on {c['service_date']} ({c['status']})" for c in claims)
            return {"answer": f"Here are the claims on your account:\n{listing}\n\nWhich one would you like details on?",
                    "trace": trace + ["claims_agent:list"]}

        lookup = self.d.claims.get_claim(claim_id, member_id)
        if not lookup.found:
            guard = dict(state["guardrail"])
            if not lookup.authorized:
                guard["flags"] = guard.get("flags", []) + ["tool_authz_denied"]
                logger.warning("claim access denied", extra={"extra_fields": {"claim_id": claim_id, "member_id": member_id}})
            return {"answer": lookup.message, "guardrail": guard, "trace": trace + ["claims_agent:not_found"]}

        claim = lookup.claim
        update = {"claim": claim, "trace": trace + [f"claims_agent:{claim['status']}"]}
        # Agent collaboration: if a claim is denied/pending, ask the policy agent
        # for the rules that explain the denial and what the member can do next.
        if claim.get("denial_code"):
            update["search_query"] = (
                f"{claim['denial_code']} {claim['denial_reason']} how to fix or appeal; {state['standalone_question']}"
            )
        return update

    # --------------------------------------------------- policy RAG agent ---
    def retrieve(self, state: AgentState) -> dict:
        query = state.get("search_query") or state["standalone_question"]
        chunks = self.d.kb.search(query, k=self.s.retrieval_k)
        return {"documents": [c.to_dict() for c in chunks], "trace": state["trace"] + [f"retrieve:{len(chunks)}"]}

    def grade_documents(self, state: AgentState) -> dict:
        docs = state.get("documents", [])
        if not docs or not self.s.enable_doc_grading:
            return {"trace": state["trace"] + ["grade:skipped"]}
        numbered = "\n\n".join(f"Chunk {i}:\n{d['content'][:1200]}" for i, d in enumerate(docs, start=1))
        result = invoke_structured(
            self.d.llm,
            GradeResult,
            [
                SystemMessage(content=prompts.GRADER_SYSTEM),
                HumanMessage(content=f"Question: {state['standalone_question']}\n\n{numbered}"),
            ],
            default=GradeResult(relevant_ids=list(range(1, len(docs) + 1))),  # fail open: keep all
        )
        keep = [docs[i - 1] for i in result.relevant_ids if 1 <= i <= len(docs)]
        return {"documents": keep, "trace": state["trace"] + [f"grade:{len(keep)}/{len(docs)}"]}

    def rewrite_query(self, state: AgentState) -> dict:
        result = invoke_structured(
            self.d.llm,
            RewriteResult,
            [SystemMessage(content=prompts.REWRITE_SYSTEM), HumanMessage(content=state["standalone_question"])],
            default=RewriteResult(query=state["standalone_question"]),
        )
        return {"search_query": result.query, "rewrites": state.get("rewrites", 0) + 1,
                "trace": state["trace"] + ["rewrite_query"]}

    def fallback(self, state: AgentState) -> dict:
        return {"answer": prompts.FALLBACK_REPLY, "grounded": None, "trace": state["trace"] + ["fallback:escalate"]}

    def generate(self, state: AgentState) -> dict:
        strict = prompts.STRICT_ADDENDUM if state.get("regenerations", 0) > 0 else ""
        system = prompts.ANSWER_SYSTEM.format(context=_build_context(state), strict=strict)
        history = state.get("messages", [])[:-1][-self.s.history_window:]
        msgs = [SystemMessage(content=system), *history, HumanMessage(content=state["standalone_question"])]
        answer = self.d.llm.invoke(msgs).content
        citations = [
            {"id": i, "source": d["source"], "section": d.get("section", ""), "score": d.get("score")}
            for i, d in enumerate(state.get("documents", []), start=1)
        ]
        if state.get("claim"):
            citations.insert(0, {"id": "CLAIM", "source": f"claims-system:{state['claim']['claim_id']}", "section": "", "score": None})
        answer = str(answer).strip()
        if state.get("claim"):
            # Facts we already hold as structured data are stated deterministically, not left to the LLM.
            answer = f"{claim_summary(state['claim'])}\n\n{answer}"
        return {"answer": answer, "citations": citations, "trace": state["trace"] + ["generate"]}

    # ------------------------------------------------------------ critic ---
    def groundedness_check(self, state: AgentState) -> dict:
        """Critic. Two complementary checks, selected by GROUNDEDNESS_MODE:
        - numeric: every $ amount / % in the answer must exist in the context
          (deterministic; catches the most harmful hallucinations - wrong money)
        - llm:     LLM fact-checker over all claims (needs a strong model; a 3B
          model produced false rejections in our eval, so local default is numeric)
        """
        if not self.s.enable_groundedness_check:
            return {"grounded": None, "trace": state["trace"] + ["groundedness:skipped"]}
        context = _build_context(state)
        mode = self.s.groundedness_mode
        grounded, detail = True, ""
        if mode in ("numeric", "both"):
            bad = unsupported_numbers(state["answer"], context)
            if bad:
                grounded, detail = False, f"numbers:{','.join(bad)}"
        if grounded and mode in ("llm", "both"):
            result = invoke_structured(
                self.d.llm,
                GroundednessResult,
                [
                    SystemMessage(content=prompts.GROUNDEDNESS_SYSTEM),
                    HumanMessage(content=f"CONTEXT:\n{context}\n\nANSWER:\n{state['answer']}"),
                ],
                default=GroundednessResult(grounded=True),
            )
            grounded, detail = result.grounded, "llm"
        tag = f"groundedness:{grounded}" + (f"({detail})" if not grounded else "")
        update: dict = {"grounded": grounded, "trace": state["trace"] + [tag]}
        if not grounded:
            update["regenerations"] = state.get("regenerations", 0) + 1
        return update

    def output_guard(self, state: AgentState) -> dict:
        # The groundedness critic gave up: prefer a safe escalation over a possibly-wrong answer.
        answer = state.get("answer", "")
        if state.get("grounded") is False:
            answer = prompts.FALLBACK_REPLY
            if state.get("claim"):  # keep the deterministic (always-correct) claim facts
                answer = f"{claim_summary(state['claim'])}\n\n{answer}"
        result = self.d.guardrails.check_output(answer, context=_build_context(state), query=state.get("standalone_question", ""))
        guard = dict(state["guardrail"])
        guard["flags"] = guard.get("flags", []) + result.flags
        if result.blocked:
            guard["blocked"], guard["reason"] = True, result.reason
            final = BLOCKED_MESSAGE
        else:
            final = result.text
        return {"answer": final, "guardrail": guard, "trace": state["trace"] + ["output_guard"]}

    def finalize(self, state: AgentState) -> dict:
        return {"messages": [AIMessage(content=state["answer"])], "trace": state["trace"] + ["finalize"]}
