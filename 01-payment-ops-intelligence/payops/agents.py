"""The six agents. Each is a LangGraph node that reads shared state and writes its own output.

Intent Agent          classifies the request (RCA / Trend / Recommendation / Summary / Search) and filters
Search Agent          hybrid semantic search over historical incidents (+ reports/rules)   - no LLM
RCA Agent             probable causes from similar historical failures                       - LLM
Recommendation Agent  actions from past resolutions + business rules                         - LLM
Trend Agent           pandas analytics (counts, severity, MTTR, month-end share) + narrative - LLM narrates only
Summary Agent         executive / operational summary tailored to the caller's role          - LLM

Every LLM agent has a deterministic fallback, so a model outage degrades the answer instead of failing it.
"""

import logging
import re
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from payops import analytics
from payops.config import Settings
from payops.llm import structured

log = logging.getLogger(__name__)

INTENTS = ("search", "rca", "recommendation", "trend", "summary")
CATEGORIES = ("bank_file_rejection", "duplicate_payment", "payment_timeout", "invalid_routing_number",
              "reconciliation_mismatch", "credential_expiry", "settlement_delay")
SYSTEMS = ("Bank File Transfer", "Payment Gateway", "Vendor Master", "Invoice Matching", "Settlement Engine")

CATEGORY_KEYWORDS = {
    "duplicate_payment": ("duplicate", "paid twice", "double pay", "twice"),
    "payment_timeout": ("timeout", "timed out", "time out", "latency", "stalled"),
    "bank_file_rejection": ("nacha", "ach file", "bank file", "file reject", "batch control"),
    "invalid_routing_number": ("routing", "aba", "r03", "bank details"),
    "reconciliation_mismatch": ("reconcil", "mismatch", "variance", "rounding", "out of balance"),
    "credential_expiry": ("certificate", "sftp", "credential", "authentication", "expired"),
    "settlement_delay": ("settlement", "cut-off", "cutoff", "late settle", "missed window"),
}
SYSTEM_KEYWORDS = {
    "Bank File Transfer": ("bank file", "sftp", "file transfer"),
    "Payment Gateway": ("gateway",),
    "Vendor Master": ("vendor master", "master data"),
    "Invoice Matching": ("invoice match",),
    "Settlement Engine": ("settlement engine",),
}
INTENT_KEYWORDS = {
    "rca": ("why", "root cause", "caus", "rca", "reason", "what went wrong"),
    "recommendation": ("recommend", "should we", "what should", "prevent", "next step", "how do we fix", "avoid", "action"),
    "trend": ("trend", "pattern", "recurring", "monthly", "over time", "increas", "rising", "how many", "count", "metric", "spike"),
    "summary": ("summar", "executive", "overview", "brief", "status report", "leadership"),
    "search": ("find", "show", "list", "similar", "search", "look up", "incidents like", "past incidents"),
}
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august",
                                     "september", "october", "november", "december"], start=1)}


class IntentDecision(BaseModel):
    """How to handle a payment-operations request."""

    intent: Literal[INTENTS] = Field(description="search | rca | recommendation | trend | summary")  # type: ignore[valid-type]
    also_recommend: bool = Field(default=False, description="True if the user also asks what to do about it")
    category: Literal[CATEGORIES] | None = Field(default=None, description="failure category, if one is named")  # type: ignore[valid-type]
    system: Literal[SYSTEMS] | None = None  # type: ignore[valid-type]
    payment_type: Literal["ACH", "Wire", "Check"] | None = None
    months: list[str] = Field(default_factory=list, description="months mentioned, as YYYY-MM (year 2026)")
    confidence: float = Field(ge=0, le=1)


INTENT_PROMPT = f"""You route requests from a payment operations team. Choose ONE intent:
- search: find / list past incidents ("show incidents like...", "find similar failures")
- rca: why something failed, root cause analysis
- recommendation: what to do / how to prevent or fix
- trend: patterns, counts, recurring failures, metrics over time
- summary: executive or operational summary / overview of payment health
Set also_recommend=true when an RCA question also asks what to do.
Failure categories: {', '.join(CATEGORIES)}. Systems: {', '.join(SYSTEMS)}.
Examples:
"Why did the ACH file get rejected yesterday?" -> rca, category=bank_file_rejection
"Why are we paying vendors twice and how do we stop it?" -> rca, also_recommend=true, category=duplicate_payment
"Are duplicate payments increasing since August?" -> trend, category=duplicate_payment
"Give leadership a summary of September payment health" -> summary, months=[2026-09]
"Find past incidents like a wire rejected for a bad routing number" -> search, category=invalid_routing_number"""


def keyword_intent(question: str) -> IntentDecision:
    q = question.lower()
    hits = {i: sum(k in q for k in kws) for i, kws in INTENT_KEYWORDS.items()}
    best = max(hits, key=hits.get)
    intent = best if hits[best] else "search"
    if hits["rca"] and hits["recommendation"]:
        intent = "rca"  # "why ... and what should we do" = RCA followed by recommendations
    cat_hits = {c: sum(k in q for k in kws) for c, kws in CATEGORY_KEYWORDS.items()}
    category = max(cat_hits, key=cat_hits.get) if max(cat_hits.values()) else None
    months = [f"2026-{n:02d}" for name, n in MONTHS.items() if name in q]
    return IntentDecision(intent=intent, also_recommend=intent == "rca" and hits["recommendation"] > 0,
                          category=category, months=months, confidence=0.5 if hits[best] else 0.3)


def ground_filters(d: IntentDecision, question: str) -> IntentDecision:
    """Slot grounding: small models invent filters (a system, a payment type, months in the wrong year).
    Keep an extracted filter only if the question actually mentions it."""
    q = question.lower()
    if d.system and not any(k in q for k in SYSTEM_KEYWORDS[d.system]):
        d.system = None
    if d.payment_type and d.payment_type.lower() not in q:
        d.payment_type = None
    mentioned = {f"2026-{n:02d}" for name, n in MONTHS.items() if name in q or name[:3] + " " in q}
    mentioned |= set(re.findall(r"\b20\d\d-\d\d\b", q))
    d.months = sorted(m for m in d.months if m in mentioned) or sorted(mentioned)
    if d.category and not any(k in q for k in CATEGORY_KEYWORDS[d.category]):
        d.category = keyword_intent(question).category
    return d


class PaymentAgents:
    def __init__(self, llm: BaseChatModel, retrievers: dict, settings: Settings):
        self.llm, self.retrievers, self.s = llm, retrievers, settings

    # ------------------------------------------------------------------ helpers
    def _llm(self, system: str, user: str, fallback: str) -> tuple[str, bool]:
        try:
            msg = self.llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
            text = str(msg.content).strip()
            return (text, True) if text else (fallback, False)
        except Exception as exc:  # noqa: BLE001 - degrade to the deterministic answer
            log.warning("LLM call failed, using fallback: %s", exc)
            return fallback, False

    # ------------------------------------------------------------------ Intent Agent
    def classify(self, question: str) -> tuple[IntentDecision, str]:
        try:
            d = structured(self.llm, IntentDecision).invoke(
                [SystemMessage(content=INTENT_PROMPT), HumanMessage(content=question)])
            if d is None:
                raise ValueError("no decision")
            if d.confidence < self.s.intent_confidence_threshold:
                kw = keyword_intent(question)
                if kw.confidence >= 0.5:
                    return kw, "keyword (low LLM confidence)"
            # Keep the LLM intent but fill a category it missed from keywords.
            if d.category is None:
                d.category = keyword_intent(question).category
            return ground_filters(d, question), "llm"
        except Exception as exc:  # noqa: BLE001
            log.warning("Intent LLM failed (%s); keyword fallback", exc)
            return keyword_intent(question), "keyword-fallback"

    # ------------------------------------------------------------------ Search Agent
    def search(self, question: str, intent: dict) -> dict:
        where = {"failure_category": intent["category"]} if intent.get("category") else None
        hits = self.retrievers["incidents"].search(question, self.s.search_top_k, where)
        if len(hits) < 2 and where:  # filter too narrow - search everything
            hits = self.retrievers["incidents"].search(question, self.s.search_top_k)
        hits = [h for h in hits if h["score"] >= self.s.min_relevance] or hits[:3]
        knowledge = self.retrievers["knowledge"].search(question, self.s.knowledge_top_k)
        knowledge = [k for k in knowledge if k["score"] >= self.s.min_relevance]
        listing = "\n".join(
            f"- {h['metadata']['incident_id']} ({h['metadata']['date']}, {h['metadata']['severity']}, "
            f"{h['metadata']['failure_category']}): {h['content'].splitlines()[1].removeprefix('Title: ')} "
            f"- root cause: {_field(h['content'], 'Root cause')}"
            for h in hits
        )
        return {"incidents": hits, "knowledge": knowledge,
                "answer": f"Most similar historical incidents:\n{listing}" if hits else "No similar incidents found."}

    # ------------------------------------------------------------------ RCA Agent
    def rca(self, question: str, search: dict) -> dict:
        evidence = "\n\n".join(h["content"] for h in search["incidents"])
        top = search["incidents"][:3]
        fallback = "Probable causes, based on the most similar past incidents:\n" + "\n".join(
            f"- {_field(h['content'], 'Root cause')} (seen in {h['metadata']['incident_id']})" for h in top)
        text, used = self._llm(
            "You are a payment operations root-cause analyst. Using ONLY the historical incidents provided, "
            "list the most probable root causes (most likely first). For each: one sentence, the supporting "
            "incident IDs in brackets, and how common it is in the evidence. Do not invent numbers or IDs. "
            "Max 5 bullets.",
            f"Question: {question}\n\nHistorical incidents:\n{evidence}", fallback)
        return {"answer": text, "evidence": evidence, "llm": used}

    # ------------------------------------------------------------------ Recommendation Agent
    def recommend(self, question: str, search: dict, rca: dict | None) -> dict:
        rules = self.retrievers["knowledge"].search(question + " rules runbook", self.s.knowledge_top_k,
                                                    {"doc_type": "business_rules"})
        resolutions = "\n".join(f"- {h['metadata']['incident_id']}: {_field(h['content'], 'Resolution')}"
                                for h in search["incidents"])
        rules_text = "\n\n".join(r["content"] for r in rules)
        fallback = "Actions that resolved similar incidents:\n" + resolutions
        text, used = self._llm(
            "You recommend operational actions for a payment operations team. Use ONLY the past resolutions and "
            "the business rules provided. Give 3-6 numbered actions, most urgent first; after each action cite the "
            "incident ID or rule document ID (PAY-RULES-001) it comes from. You are advisory: never tell the user "
            "that you executed anything.",
            f"Question: {question}\n\nRoot cause analysis:\n{(rca or {}).get('answer', 'n/a')}\n\n"
            f"Past resolutions:\n{resolutions}\n\nBusiness rules:\n{rules_text}", fallback)
        return {"answer": text, "evidence": resolutions + "\n" + rules_text, "rules": rules, "llm": used}

    # ------------------------------------------------------------------ Trend Agent
    def trend(self, question: str, intent: dict) -> dict:
        report = analytics.trend_report(intent.get("category"), intent.get("system"), intent.get("payment_type"),
                                        intent.get("months") or None)
        table = analytics.render(report)
        fallback = table
        text, used = self._llm(
            "You are a payment operations analyst. Explain the trend in 3-6 bullets using ONLY the numbers in the "
            "analytics table (copy them exactly). Call out rising categories, month-end effects and severity. "
            "No numbers that are not in the table.",
            f"Question: {question}\n\nAnalytics:\n{table}", fallback)
        return {"answer": text, "report": report, "evidence": table, "llm": used}

    # ------------------------------------------------------------------ Summary Agent
    def summary(self, question: str, trend: dict, style: str) -> dict:
        recent = analytics.recent_high_severity()
        recent_text = "\n".join(f"- {r['incident_id']} {r['date']} {r['severity']} {r['failure_category']}: "
                                f"{r['title']} (${r['amount_usd']:,.2f})" for r in recent)
        commentary = self.retrievers["knowledge"].search("executive commentary " + question, 3,
                                                         {"doc_type": "monitoring_report"})
        commentary_text = "\n\n".join(c["content"] for c in commentary)
        evidence = f"{trend['evidence']}\n\nRecent Sev1/Sev2:\n{recent_text}\n\nReports:\n{commentary_text}"
        audience = ("executives: 4-5 short bullets on business impact, risk and what is being done; no jargon"
                    if style == "executive" else
                    "the operations team: status, top issues with incident IDs, open risks, next actions")
        fallback = f"Payment operations summary\n{trend['evidence']}\n\nRecent high-severity incidents:\n{recent_text}"
        text, used = self._llm(
            f"Write a concise payment operations summary for {audience}. Use ONLY the facts provided and copy "
            "numbers exactly.", f"Request: {question}\n\nFacts:\n{evidence}", fallback)
        return {"answer": text, "evidence": evidence, "llm": used}


def _field(content: str, name: str) -> str:
    m = re.search(rf"^{name}: (.*)$", content, re.MULTILINE)
    return m.group(1) if m else ""
