"""Deterministic guardrails for a regulated (GxP) knowledge assistant.

Input : length, prompt injection, medical / dosing advice (out of scope), release / disposition commands
        (QA decides - the assistant informs), PII redaction.
Output: numeric grounding (temperatures, durations, quantities), identifier grounding (LOT-, SHP-, DEV-,
        SOP-, CAPA-, SUP- IDs must exist in the retrieved context), PII redaction.
Access control is enforced before retrieval (classification filter), not by the LLM.
"""

import re
from dataclasses import dataclass, field

INJECTION = [
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|all|your)\b.{0,20}\b(instructions?|prompts?|rules?)",
    r"\b(reveal|show|print|repeat)\b.{0,20}\b(system|hidden)\s+(prompt|instructions?)",
    r"\byou are (now|no longer)\b",
    r"\bjailbreak\b|\bdeveloper mode\b",
    r"\b(show|give|list)\b.{0,30}\b(confidential|restricted)\b.{0,20}\b(documents?|files?)\b.{0,30}\b(anyway|regardless|even if)",
]
MEDICAL = [
    r"\b(what|which|how much)\b.{0,20}\b(dose|dosage|mg)\b.{0,40}\b(patient|child|adult|give|take|administer)",
    r"\b(can|should|is it safe (for|to))\b.{0,30}\b(patients?|i|we)\b.{0,30}\b(take|use|inject|administer)\b",
    r"\b(side effects?|contraindications?|interactions?)\b.{0,30}\b(patient|my|for me)\b",
]
_COMMAND = r"^(?:please\s+|go ahead and\s+|(?:can|could|would|will) you\s+(?:please\s+)?|i need you to\s+)?"
ACTIONS = [_COMMAND + r"(release|approve|reject|quarantine|disposition|ship|recall|destroy)\b.{0,40}\b(lots?|lot-\d+|batch(es)?|shipments?|product)\b"]
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")
MESSAGES = {
    "prompt_injection": "I can only answer from the documents you're cleared to see. Please rephrase your question.",
    "medical_advice": "I can't give medical or dosing advice. I answer supply-chain and quality questions only - "
                      "please consult the product label or a healthcare professional.",
    "action_request": "I can't release, reject, quarantine or recall product - those are QA decisions recorded in the "
                      "quality system. I can explain the procedure or summarise the evidence.",
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
    for pattern, label in ((EMAIL, "email"), (PHONE, "phone")):
        if pattern.search(text):
            text, flags = pattern.sub(f"[{label}]", text), flags + [f"redacted_{label}"]
    return text, flags


def check_input(question: str, max_chars: int = 1000) -> InputCheck:
    q = " ".join(question.split())
    if len(q) > max_chars:
        return InputCheck(False, q[:max_chars], "too_long", MESSAGES["too_long"].format(max=max_chars))
    q, flags = redact(q)
    low = q.lower()
    for cat, patterns in (("prompt_injection", INJECTION), ("medical_advice", MEDICAL), ("action_request", ACTIONS)):
        if any(re.search(p, low) for p in patterns):
            return InputCheck(False, q, cat, MESSAGES[cat], flags)
    return InputCheck(True, q, flags=flags)


NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
IDS = re.compile(r"\b(?:LOT|SHP|DEV|SOP|CAPA|SUP|GDP|INV)-[\w-]*\d[\w-]*\b")
CITE = re.compile(r"\[\d+(?:\s*,\s*\d+)*\]")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+", re.MULTILINE)


def _norm(n: str) -> str:
    n = n.replace(",", "")
    return (n.rstrip("0").rstrip(".") if "." in n else n) or "0"


def _numbers(text: str) -> set[str]:
    return {_norm(n) for n in NUMBER.findall(IDS.sub(" ", CITE.sub(" ", text)))}


@dataclass
class OutputCheck:
    answer: str
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.startswith(("unsupported_numbers", "unknown_ids")) for i in self.issues)


def check_output(answer: str, context: str, question: str = "") -> OutputCheck:
    text, flags = redact(answer)
    out = OutputCheck(text, list(flags))
    nums = sorted(_numbers(LIST_MARKER.sub(" ", text)) - _numbers(context) - _numbers(question))
    if nums:
        out.issues.append("unsupported_numbers:" + ",".join(nums))
    unknown = sorted(set(IDS.findall(text)) - set(IDS.findall(context)) - set(IDS.findall(question)))
    if unknown:
        out.issues.append("unknown_ids:" + ",".join(unknown))
    return out
