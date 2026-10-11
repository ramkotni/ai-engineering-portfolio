"""Agents for the Robotics Fleet Assistant.

Intent Agent                classifies into 7 workflows + extracts robot ID, zone, event type
Fleet Search Agent          hybrid semantic search over incidents + maintenance logs (+ guide)        - no LLM
Robot Diagnostics Agent     probable causes (battery, sensor, motor, scanner, Wi-Fi, navigation)      - LLM
Battery Analysis Agent      30-day health slope per robot vs battery policy                           - LLM narrates
Predictive Maintenance Agent risk score per robot + policy-based proactive actions                    - LLM narrates
Task Optimization Agent     workload rebalancing proposals within each zone                           - LLM narrates
Fleet Status Agent          status / utilisation per zone                                              - no LLM
Operations Summary Agent    daily warehouse health report, tailored to the caller's role              - LLM

Agents earlier in a plan run in data-only mode; only the final agent writes a narrative (saves LLM calls).
"""

import logging
import re
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from fleetops import analytics
from fleetops.config import Settings
from fleetops.data import robot_text, table
from fleetops.llm import structured

log = logging.getLogger(__name__)

INTENTS = ("robot_diagnostics", "fleet_status", "battery_analysis", "navigation_issues", "predictive_maintenance",
           "task_assignment", "operational_summary")
ZONES = ("Z1-Inbound", "Z2-Storage", "Z3-Pick", "Z4-Pack")
EVENT_TYPES = ("battery_degradation", "sensor_fault", "motor_fault", "barcode_scanner_error", "wifi_drop",
               "navigation_exception")
ROBOT_ID = re.compile(r"\bR-?(\d{4})\b", re.IGNORECASE)

INTENT_KEYWORDS = {
    "robot_diagnostics": ("why", "diagnos", "fault", "error", "keeps stopping", "stopped", "failing", "broken", "alarm", "code"),
    "navigation_issues": ("navigat", "path", "lost locali", "stuck", "route", "map", "wi-fi", "wifi", "roaming", "connectivity"),
    "battery_analysis": ("battery", "charge", "state of health", "degrad"),
    "predictive_maintenance": ("predictive", "maintenance", "proactive", "at risk", "likely to fail", "service next", "schedule"),
    "task_assignment": ("reassign", "workload", "balanc", "overload", "task assignment", "redistribut", "utiliz", "utilis"),
    "fleet_status": ("status", "how many robots", "fleet health", "active", "available", "down"),
    "operational_summary": ("summar", "daily report", "health report", "executive", "overview", "shift report"),
}
ZONE_KEYWORDS = {"Z1-Inbound": ("z1", "inbound"), "Z2-Storage": ("z2", "storage"), "Z3-Pick": ("z3", "pick"),
                 "Z4-Pack": ("z4", "pack")}
EVENT_KEYWORDS = {"battery_degradation": ("battery",), "sensor_fault": ("lidar", "sensor", "bumper"),
                  "motor_fault": ("motor", "encoder", "wheel"), "barcode_scanner_error": ("barcode", "scanner", "fiducial"),
                  "wifi_drop": ("wi-fi", "wifi", "network", "roaming", "access point"),
                  "navigation_exception": ("navigat", "path", "localisation", "localization", "stuck")}


class IntentDecision(BaseModel):
    """How to handle a robotics operations request."""

    intent: Literal[INTENTS]  # type: ignore[valid-type]
    robot_id: str | None = Field(default=None, description="robot ID like R-1007 if one is named")
    zone: Literal[ZONES] | None = None  # type: ignore[valid-type]
    event_type: Literal[EVENT_TYPES] | None = None  # type: ignore[valid-type]
    confidence: float = Field(ge=0, le=1)


INTENT_PROMPT = f"""You route requests from a warehouse robotics team. Choose ONE intent:
- robot_diagnostics: why a robot fails / stops / shows an error code
- navigation_issues: path planning, localisation, stuck robots, Wi-Fi / roaming problems
- battery_analysis: battery health, degradation, charging
- predictive_maintenance: which robots need maintenance soon, proactive actions
- task_assignment: workload balancing, which tasks to reassign, overloaded robots
- fleet_status: how many robots are active / down, utilisation per zone
- operational_summary: daily health report or summary for leaders
Zones: {', '.join(ZONES)}. Event types: {', '.join(EVENT_TYPES)}.
Examples: "Why does R-1007 keep returning to the charger?" -> robot_diagnostics, robot_id=R-1007
"Robots in the pick zone keep losing Wi-Fi" -> navigation_issues, zone=Z3-Pick, event_type=wifi_drop
"Which robots should we service next week?" -> predictive_maintenance
"Rebalance tasks in Z3" -> task_assignment, zone=Z3-Pick"""


def keyword_intent(question: str) -> IntentDecision:
    q = question.lower()
    hits = {i: sum(k in q for k in kws) for i, kws in INTENT_KEYWORDS.items()}
    if hits["battery_analysis"] and (hits["robot_diagnostics"] or hits["predictive_maintenance"]) and "battery" in q:
        hits["battery_analysis"] += 1 if "health" in q or "degrad" in q else 0
    best = max(hits, key=hits.get)
    m = ROBOT_ID.search(question)
    zone = next((z for z, kws in ZONE_KEYWORDS.items() if any(re.search(rf"\b{k}\b", q) for k in kws)), None)
    ev_hits = {e: sum(k in q for k in kws) for e, kws in EVENT_KEYWORDS.items()}
    event = max(ev_hits, key=ev_hits.get) if max(ev_hits.values()) else None
    return IntentDecision(intent=best if hits[best] else "fleet_status", robot_id=f"R-{m.group(1)}" if m else None,
                          zone=zone, event_type=event, confidence=0.5 if hits[best] else 0.3)


def ground_filters(d: IntentDecision, question: str) -> IntentDecision:
    """Keep extracted slots only if the question mentions them (small models invent IDs and zones)."""
    kw = keyword_intent(question)
    d.robot_id = kw.robot_id
    if d.zone and d.zone != kw.zone:
        d.zone = kw.zone
    if d.event_type and not any(k in question.lower() for k in EVENT_KEYWORDS[d.event_type]):
        d.event_type = kw.event_type
    return d


class FleetAgents:
    def __init__(self, llm: BaseChatModel, retrievers: dict, settings: Settings):
        self.llm, self.retrievers, self.s = llm, retrievers, settings

    def _llm(self, system: str, user: str, fallback: str) -> tuple[str, bool]:
        try:
            text = str(self.llm.invoke([SystemMessage(content=system), HumanMessage(content=user)]).content).strip()
            return (text, True) if text else (fallback, False)
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM failed, deterministic fallback: %s", exc)
            return fallback, False

    def classify(self, question: str) -> tuple[IntentDecision, str]:
        try:
            d = structured(self.llm, IntentDecision).invoke([SystemMessage(content=INTENT_PROMPT), HumanMessage(content=question)])
            if d is None:
                raise ValueError("no decision")
            if d.confidence < self.s.intent_confidence_threshold and keyword_intent(question).confidence >= 0.5:
                return keyword_intent(question), "keyword (low LLM confidence)"
            return ground_filters(d, question), "llm"
        except Exception as exc:  # noqa: BLE001
            log.warning("Intent LLM failed (%s); keyword fallback", exc)
            return keyword_intent(question), "keyword-fallback"

    # ------------------------------------------------------------------ Fleet Search Agent
    def search(self, question: str, intent: dict, zones: list[str]) -> dict:
        where: dict = {}
        if zones:
            where["zone"] = zones
        if intent.get("robot_id"):
            where["robot_id"] = intent["robot_id"]
        elif intent.get("event_type"):
            where["event_type"] = intent["event_type"]
        elif intent.get("zone"):
            where["zone"] = [intent["zone"]] if not zones else [z for z in zones if z == intent["zone"]]
        hits = self.retrievers["events"].search(question, self.s.search_top_k, where or None)
        if intent.get("robot_id"):  # add fleet-wide similar incidents for the same error pattern
            more = self.retrievers["events"].search(question, self.s.search_top_k, {"zone": zones} if zones else None)
            hits += [h for h in more if h["id"] not in {x["id"] for x in hits}][:3]
        guide = self.retrievers["knowledge"].search(question, self.s.knowledge_top_k)
        listing = "\n".join(f"- {h['id']} ({h['metadata']['date']}, {h['metadata']['robot_id']}, "
                            f"{h['metadata'].get('event_type', h['metadata'].get('action'))}): {h['content'].splitlines()[1]}"
                            for h in hits)
        return {"events": hits, "guide": guide, "evidence": "\n\n".join(h["content"] for h in hits + guide),
                "answer": f"Related incidents and maintenance records:\n{listing}" if hits else "No related records found."}

    # ------------------------------------------------------------------ Robot Diagnostics Agent
    def diagnostics(self, question: str, intent: dict, search: dict, final: bool) -> dict:
        robot = ""
        if intent.get("robot_id"):
            r = table("robots")
            row = r[r.robot_id == intent["robot_id"]]
            robot = robot_text(row.iloc[0]) if len(row) else ""
        evidence = f"Robot record: {robot or 'n/a'}\n\n{search['evidence']}"
        top = [h for h in search["events"] if h["metadata"].get("doc_type") == "incident"][:3]
        fallback = "Probable causes from similar incidents:\n" + "\n".join(
            f"- {_field(h['content'], 'Root cause')} ({h['id']}); fix: {_field(h['content'], 'Resolution')}" for h in top)
        text, used = self._llm(
            "You are a robotics maintenance engineer. Using ONLY the robot record, incidents, maintenance logs and the "
            "troubleshooting guide provided, list the most probable causes (most likely first) among: battery degradation, "
            "sensor issues, motor faults, barcode scanner errors, Wi-Fi connectivity, navigation exceptions. For each cause give "
            "the supporting event IDs and the first action from the guide. Never suggest disabling safety systems. Max 5 bullets.",
            f"Question: {question}\n\n{evidence}", fallback)
        return {"answer": text, "evidence": evidence, "llm": used}

    # ------------------------------------------------------------------ Battery Analysis Agent
    def battery(self, question: str, intent: dict, zones: list[str], final: bool) -> dict:
        data = analytics.battery_analysis(zones or None, intent.get("robot_id"))
        table_text = analytics.render("battery", data)
        if not final:
            return {"answer": table_text, "evidence": table_text, "data": data, "llm": False}
        text, used = self._llm(
            "Explain battery health for a robotics team in 3-5 bullets using ONLY the numbers in the table (copy them exactly). "
            "Apply the policy: replace below 75% health or above 1,800 cycles; inspect within 7 days if decline exceeds 0.3%/day.",
            f"Question: {question}\n\n{table_text}", table_text)
        return {"answer": text, "evidence": table_text, "data": data, "llm": used}

    # ------------------------------------------------------------------ Predictive Maintenance Agent
    def maintenance(self, question: str, zones: list[str], battery: dict | None, final: bool) -> dict:
        risk = analytics.maintenance_risk(zones or None)
        policy = self.retrievers["knowledge"].search("battery policy preventive maintenance intervals", 2)
        evidence = analytics.render("risk", risk) + "\n\n" + (battery or {}).get("evidence", "") + "\n\n" + \
            "\n\n".join(p["content"] for p in policy)
        if not final:
            return {"answer": analytics.render("risk", risk), "evidence": evidence, "data": risk, "llm": False}
        text, used = self._llm(
            "You plan proactive robot maintenance. Using ONLY the risk table, battery data and policy provided, list the robots to "
            "service first with the reason and the recommended action and timeframe from the policy. Copy numbers exactly.",
            f"Question: {question}\n\n{evidence}", analytics.render("risk", risk))
        return {"answer": text, "evidence": evidence, "data": risk, "llm": used}

    # ------------------------------------------------------------------ Fleet Status Agent (deterministic)
    def fleet_status(self, zones: list[str]) -> dict:
        data = analytics.fleet_status(zones or None)
        text = analytics.render("fleet_status", data)
        return {"answer": "Fleet status\n" + text, "evidence": text, "data": data, "llm": False}

    # ------------------------------------------------------------------ Task Optimization Agent
    def task_optimization(self, question: str, zones: list[str], final: bool) -> dict:
        data = analytics.rebalance(zones or None)
        rules = self.retrievers["knowledge"].search("workload balancing rules reassign", 1)
        evidence = analytics.render("rebalance", data) + "\n\n" + "\n\n".join(r["content"] for r in rules)
        text, used = self._llm(
            "You recommend workload balancing for warehouse robots. Explain the proposed task moves (copy robot IDs and numbers "
            "exactly) and why they follow the balancing rules. State that the shift lead executes moves in the fleet console.",
            f"Question: {question}\n\n{evidence}", "Recommended task moves (execute in the fleet console):\n" +
            analytics.render("rebalance", data))
        return {"answer": text, "evidence": evidence, "data": data, "llm": used}

    # ------------------------------------------------------------------ Operations Summary Agent
    def summary(self, question: str, outputs: dict, zones: list[str], style: str) -> dict:
        inc = table("incidents")
        if zones:
            inc = inc[inc.zone.isin(zones)]
        last7 = inc[inc.date >= max(inc.date)[:8] + "24"] if len(inc) else inc
        recent = "\n".join(f"- {r.event_id} {r.date} {r.robot_id} {r.event_type} ({r.severity})" for r in last7.itertuples())
        facts = "\n\n".join(o["evidence"] for o in outputs.values() if "evidence" in o) + f"\n\nIncidents in the last week:\n{recent}"
        audience = ("site executives: 4-5 bullets on fleet health, risk and actions, no jargon" if style == "executive"
                    else "the operations team: fleet status, top risks with robot IDs, recent incidents, actions for today")
        text, used = self._llm(f"Write a daily warehouse robotics health report for {audience}. Use ONLY the facts and copy numbers exactly.",
                               f"Request: {question}\n\nFacts:\n{facts}", "Daily fleet health report\n" + facts)
        return {"answer": text, "evidence": facts, "llm": used}


def _field(content: str, name: str) -> str:
    m = re.search(rf"^{name}: (.*)$", content, re.MULTILINE)
    return m.group(1) if m else ""
