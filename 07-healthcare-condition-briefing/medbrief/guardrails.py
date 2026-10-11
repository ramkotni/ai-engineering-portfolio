"""Deterministic guardrails for a strategy (non-clinical) briefing tool.

Input : length, prompt injection, patient-specific medical advice (the tool informs strategy, it does not treat
        patients), PHI / PII redaction (MRN, date of birth, SSN, phone, email).
Output: numeric grounding (every number must appear in the evidence), identifier grounding (trial and document IDs
        must exist in the evidence), second-person treatment advice is flagged, PHI redaction.
Access control (clearance, live data) is enforced in code before retrieval, not by the LLM.
"""

import re
from dataclasses import dataclass, field

INJECTION = [
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|all|your)\b.{0,20}\b(instructions?|prompts?|rules?)",
    r"\b(reveal|show|print|repeat)\b.{0,20}\b(system|hidden)\s+(prompt|instructions?)",
    r"\byou are (now|no longer)\b",
    r"\bjailbreak\b|\bdeveloper mode\b",
    r"\b(show|give|include)\b.{0,30}\b(internal|confidential|restricted)\b.{0,30}\b(anyway|regardless|even if)",
]
_PERSON = r"(i|me|my|he|she|him|her|we|my (?:patient|mother|father|mom|dad|wife|husband|son|daughter|child|partner|friend))"
PATIENT_ADVICE = [
    rf"\b(should|can|could|do|must)\s+{_PERSON}\b.{{0,40}}\b(take|start|stop|use|increase|decrease|switch|get|try)\b",
    r"\b(my|this|our)\s+(patient|mother|father|mom|dad|wife|husband|son|daughter|child|friend|partner)\b",
    r"\bdiagnos(e|is)\b.{0,10}\b(me|my|him|her)\b",
    r"\b(i have|i've been diagnosed|i was diagnosed|i am taking|i'm taking|for me)\b",
    rf"\bwhat\s+(dose|dosage)\b.{{0,30}}\b{_PERSON}\b",
]
PHI = [(re.compile(r"\bMRN[:#\s]*\d{5,}\b", re.IGNORECASE), "mrn"),
       (re.compile(r"\b(?:DOB|date of birth)[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE), "dob"),
       (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "ssn"),
       (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "email"),
       (re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"), "phone")]
MESSAGES = {
    "prompt_injection": "I can only brief from the sources you're cleared to see. Please rephrase your request.",
    "patient_advice": "I can't advise on an individual patient's diagnosis or treatment. This tool produces strategy "
                      "briefings from guideline and pipeline sources; clinical decisions belong with the treating clinician.",
    "too_long": "Please keep the request under {max} characters.",
}
DISCLAIMER = ("Strategy briefing generated from synthetic guideline summaries and a trial registry for planning purposes only - "
              "not clinical guidance. Verify against the full sources before external use.")


@dataclass
class InputCheck:
    allowed: bool
    text: str
    category: str | None = None
    message: str | None = None
    flags: list[str] = field(default_factory=list)


def redact(text: str) -> tuple[str, list[str]]:
    flags = []
    for pattern, label in PHI:
        if pattern.search(text):
            text, flags = pattern.sub(f"[{label}]", text), flags + [f"redacted_{label}"]
    return text, flags


def check_input(text: str, max_chars: int = 1000) -> InputCheck:
    t = " ".join(text.split())
    if len(t) > max_chars:
        return InputCheck(False, t[:max_chars], "too_long", MESSAGES["too_long"].format(max=max_chars))
    t, flags = redact(t)
    low = t.lower()
    for cat, patterns in (("prompt_injection", INJECTION), ("patient_advice", PATIENT_ADVICE)):
        if any(re.search(p, low) for p in patterns):
            return InputCheck(False, t, cat, MESSAGES[cat], flags)
    return InputCheck(True, t, flags=flags)


NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
IDS = re.compile(r"\b(?:SYN-(?:HF|DM)-\d+|NCT\d{8}|CARD-GL-\d+|DM-GL-\d+|STRAT-\d+|REG-\d+)\b")
CITE = re.compile(r"\[\d+(?:\s*,\s*\d+)*\]")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+", re.MULTILINE)
SECOND_PERSON_ADVICE = re.compile(r"\byou should (take|start|stop|increase|decrease|switch)\b", re.IGNORECASE)


def _norm(n: str) -> str:
    n = n.replace(",", "")
    return (n.rstrip("0").rstrip(".") if "." in n else n) or "0"


def _numbers(text: str) -> set[str]:
    return {_norm(n) for n in NUMBER.findall(IDS.sub(" ", CITE.sub(" ", text)))}


@dataclass
class OutputCheck:
    text: str
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.startswith(("unsupported_numbers", "unknown_ids", "patient_advice")) for i in self.issues)


def check_output(text: str, evidence: str, request: str = "") -> OutputCheck:
    out_text, flags = redact(text)
    out = OutputCheck(out_text, list(flags))
    # section numbering in headings and list markers is layout, not a claim
    body = LIST_MARKER.sub(" ", re.sub(r"^#+ .*$", " ", out_text, flags=re.MULTILINE))
    nums = sorted(_numbers(body) - _numbers(evidence) - _numbers(request))
    if nums:
        out.issues.append("unsupported_numbers:" + ",".join(nums))
    unknown = sorted(set(IDS.findall(out_text)) - set(IDS.findall(evidence)) - set(IDS.findall(request)))
    if unknown:
        out.issues.append("unknown_ids:" + ",".join(unknown))
    if SECOND_PERSON_ADVICE.search(out_text):
        out.issues.append("patient_advice:second_person_treatment_language")
    return out
