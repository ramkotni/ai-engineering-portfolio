"""Deterministic guardrails (run on every request, no model needed).

Input : length, prompt injection, action requests (the assistant is read-only: it never releases,
        approves, cancels or edits payments or vendor bank details), PII / bank-data redaction.
Output: numeric grounding (every number must come from retrieved incidents, analytics or the
        question), incident-ID grounding (no invented incident IDs), bank-data redaction.
"""

import re
from dataclasses import dataclass, field

INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|all|your)\b.{0,20}\b(instructions?|prompts?|rules?)",
    r"\b(reveal|show|print|repeat)\b.{0,20}\b(system|hidden)\s+(prompt|instructions?)",
    r"\byou are (now|no longer)\b",
    r"\bjailbreak\b|\bdeveloper mode\b",
]
# The assistant is advisory. COMMANDS to move money or change master data are refused; questions about
# the process ("What is the process to change vendor bank details?") are allowed.
_COMMAND = r"^(?:please\s+|kindly\s+|go ahead and\s+|(?:can|could|would|will) you\s+(?:please\s+)?|i need you to\s+)?"
ACTION_PATTERNS = [
    _COMMAND + r"(release|approve|send|submit|execute|initiate|cancel|void|reverse|re-?send|push)\b.{0,40}"
    r"\b(payments?|wires?|ach|files?|batch(es)?|refunds?)\b",
    _COMMAND + r"(change|update|modify|edit|replace)\b.{0,30}\b(vendor|bank|routing|account)\b.{0,20}\b(details?|numbers?|records?|info)",
    r"\b(transfer|move|wire)\b.{0,20}\$\s?\d",
]
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
ACCOUNT = re.compile(r"(?<![\w*])\d{9,17}(?!\d)")  # routing (9) and account numbers

BLOCK_MESSAGES = {
    "prompt_injection": "I can only help analyse payment operations data. Please rephrase your question.",
    "action_request": (
        "I'm a read-only analysis assistant: I can't release, approve, cancel or modify payments or vendor bank "
        "details. Use the payment system with the required dual approval (see PAY-RULES-001)."
    ),
    "too_long": "Please ask one specific question (under {max} characters).",
}


@dataclass
class InputCheck:
    allowed: bool
    question: str
    category: str | None = None
    message: str | None = None
    flags: list[str] = field(default_factory=list)


def redact(text: str) -> tuple[str, list[str]]:
    flags = []
    for pattern, label in ((EMAIL, "email"), (PHONE, "phone"), (ACCOUNT, "bank_number")):
        if pattern.search(text):
            text = pattern.sub(f"[{label}]", text)
            flags.append(f"redacted_{label}")
    return text, flags


def check_input(question: str, max_chars: int = 1000) -> InputCheck:
    q = " ".join(question.split())
    if len(q) > max_chars:
        return InputCheck(False, q[:max_chars], "too_long", BLOCK_MESSAGES["too_long"].format(max=max_chars))
    q, flags = redact(q)
    low = q.lower()
    if any(re.search(p, low) for p in INJECTION_PATTERNS):
        return InputCheck(False, q, "prompt_injection", BLOCK_MESSAGES["prompt_injection"], flags)
    if any(re.search(p, low) for p in ACTION_PATTERNS):
        return InputCheck(False, q, "action_request", BLOCK_MESSAGES["action_request"], flags)
    return InputCheck(True, q, flags=flags)


NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
INCIDENT_ID = re.compile(r"\bPAY-INC-\d{4}\b")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+", re.MULTILINE)


def _norm(n: str) -> str:
    n = n.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n or "0"


def _numbers(text: str) -> set[str]:
    return {_norm(n) for n in NUMBER.findall(text)}


@dataclass
class OutputCheck:
    answer: str
    issues: list[str] = field(default_factory=list)
    unsupported_numbers: list[str] = field(default_factory=list)
    unknown_incidents: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.unsupported_numbers and not self.unknown_incidents


def check_output(answer: str, evidence: str, question: str = "") -> OutputCheck:
    """`evidence` = everything the agent was allowed to use (incidents, analytics tables, rules)."""
    text, flags = redact(answer)
    result = OutputCheck(text, issues=list(flags))
    body = INCIDENT_ID.sub(" ", LIST_MARKER.sub(" ", text))
    result.unsupported_numbers = sorted(_numbers(body) - _numbers(evidence) - _numbers(question))
    known = set(INCIDENT_ID.findall(evidence))
    result.unknown_incidents = sorted(set(INCIDENT_ID.findall(text)) - known)
    if result.unsupported_numbers:
        result.issues.append("unsupported_numbers:" + ",".join(result.unsupported_numbers))
    if result.unknown_incidents:
        result.issues.append("unknown_incidents:" + ",".join(result.unknown_incidents))
    return result
