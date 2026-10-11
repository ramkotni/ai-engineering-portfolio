"""Deterministic guardrails - cheap, testable checks that run on every request, independent of
the model (they still work when the LLM verifier is switched off on a CPU-only laptop).

Input  (before routing):   size limit, prompt-injection, requests to defeat safety devices,
                            PII redaction (emails, phone numbers) before text reaches an LLM or a log.
Output (after generation): citation validity, numeric grounding (every number must come from
                            the excerpts or the question), unsafe-advice detection.

Production adds Amazon Bedrock Guardrails (content filters, denied topics, PII) on every
Bedrock call - see Settings.bedrock_guardrail_id.
"""

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------- input
INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|earlier|all|your)\b.{0,20}\b(instructions?|prompts?|rules?)",
    r"\b(reveal|show|print|repeat|output)\b.{0,20}\b(system|hidden|initial)\s+(prompt|instructions?|message)",
    r"\byou are (now|no longer)\b",
    r"\b(act|pretend|role-?play)\b.{0,15}\b(as|to be)\b.{0,30}\b(unrestricted|jailbroken|dan|developer mode)",
    r"\bjailbreak\b",
]
SAFETY_DEVICES = (
    r"(light[- ]?curtains?|interlocks?|guards?|e-?stops?|emergency[- ]stops?|safety (switch|device|relay|valve)s?|"
    r"two[- ]hand controls?|pull[- ]?cords?|relief valves?|presence[- ]sensing)"
)
PROTECTIONS = r"(lockout|lock out|loto|tagout|tag out|ppe|permits?|gloves|goggles|harness|guards?)"
# Requests for HOW to defeat a protection. Reports of a past violation ("the interlock was bypassed
# by night shift, what do I do?") are legitimate safety questions and must NOT match.
UNSAFE_REQUEST_PATTERNS = [
    rf"\b(bypass|defeat|disable|override|jumper|cheat|tape (over|down)|tie (down|back)|block out)\b.{{0,40}}\b{SAFETY_DEVICES}",
    (
        rf"\b(can|could|may|how (do|can|to)|is it (ok|okay|fine|safe) to|allowed to|quicker to|faster to)\b.{{0,40}}"
        rf"\b(skip|skipping|without|avoid|not (use|apply|wear|do))\b.{{0,25}}\b{PROTECTIONS}"
    ),
]
# Questions about removing another worker's lock are NOT blocked: SOP-SAF-001 answers them
# ("supervisors may not...") - the output check below stops an answer that would permit it.
# Advice in a generated answer that would tell a supervisor to defeat a protection.
UNSAFE_ADVICE_PATTERNS = [
    rf"\b(you (can|may|could)|it is (ok|okay|fine|safe) to|feel free to)\b.{{0,40}}\b(skip|bypass|defeat|disable|override|remove|without)\b.{{0,40}}\b({PROTECTIONS[1:-1]}|{SAFETY_DEVICES[1:-1]})",
    rf"\b(bypass|defeat|jumper|override)\b.{{0,40}}\b{SAFETY_DEVICES}",
    r"\b(you (can|may)|it is (ok|okay|fine) to)\b.{0,20}\b(remove|cut)\b.{0,30}\b(another|someone else'?s|other)\b.{0,20}\blocks?\b",
]
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!ext\. )(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")

BLOCK_MESSAGES = {
    "unsafe_request": (
        "I can't help with bypassing safety devices or skipping lockout/tagout, PPE or permits - "
        "these protections are mandatory (SOP-SAF-001, SOP-SAF-003). If a safety device is faulty or "
        "slowing production, lock out the machine and contact the EHS Manager (ext. 4400) or "
        "Maintenance (ext. 4410)."
    ),
    "prompt_injection": (
        "I can only answer questions about the plant's safety procedures, maintenance manuals and "
        "quality standards. Please rephrase your question."
    ),
    "too_long": "That question is too long. Please ask one specific question (under {max} characters).",
}


@dataclass
class InputCheck:
    allowed: bool
    question: str                   # normalised, PII-redacted text used downstream
    category: str | None = None     # why it was blocked
    message: str | None = None      # fixed response for blocked requests
    flags: list[str] = field(default_factory=list)


def redact_pii(text: str) -> tuple[str, list[str]]:
    flags = []
    if EMAIL.search(text):
        text, flags = EMAIL.sub("[email]", text), flags + ["pii_email_redacted"]
    if PHONE.search(text):
        text, flags = PHONE.sub("[phone]", text), flags + ["pii_phone_redacted"]
    return text, flags


def check_input(question: str, max_chars: int = 1000) -> InputCheck:
    q = " ".join(question.split())
    if len(q) > max_chars:
        return InputCheck(False, q[:max_chars], "too_long", BLOCK_MESSAGES["too_long"].format(max=max_chars))
    q, flags = redact_pii(q)
    lowered = q.lower()
    if any(re.search(p, lowered) for p in INJECTION_PATTERNS):
        return InputCheck(False, q, "prompt_injection", BLOCK_MESSAGES["prompt_injection"], flags)
    if any(re.search(p, lowered) for p in UNSAFE_REQUEST_PATTERNS):
        return InputCheck(False, q, "unsafe_request", BLOCK_MESSAGES["unsafe_request"], flags)
    return InputCheck(True, q, flags=flags)


# ---------------------------------------------------------------- output
CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+", re.MULTILINE)


@dataclass
class OutputCheck:
    answer: str                      # answer with invalid citation markers removed
    issues: list[str] = field(default_factory=list)
    unsupported_numbers: list[str] = field(default_factory=list)
    unsafe_advice: bool = False

    @property
    def passed(self) -> bool:
        return not self.unsupported_numbers and not self.unsafe_advice


def _normalise_number(n: str) -> str:
    """'1,450' -> '1450', '2.0' -> '2', '0.0004' -> '0.0004', '10' -> '10'."""
    n = n.replace(",", "")
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n or "0"


def _numbers(text: str) -> set[str]:
    return {_normalise_number(n) for n in NUMBER.findall(text)}


def check_output(answer: str, excerpts: list[str], question: str = "") -> OutputCheck:
    result = OutputCheck(answer)

    # 1. Citations: drop references to excerpts that do not exist; flag answers with none.
    def fix(match: re.Match) -> str:
        refs = [r.strip() for r in match.group(1).split(",")]
        valid = [r for r in refs if 1 <= int(r) <= len(excerpts)]
        if len(valid) < len(refs):
            result.issues.append(f"invalid_citation:{','.join(r for r in refs if r not in valid)}")
        return f"[{', '.join(valid)}]" if valid else ""

    result.answer = CITATION.sub(fix, answer)
    if excerpts and not CITATION.search(result.answer) and "does not cover" not in answer.lower():
        result.issues.append("no_citations")

    # 2. Numeric grounding: torques, pressures, limits, extensions must be copied, never invented.
    body = CITATION.sub(" ", LIST_MARKER.sub(" ", result.answer))
    allowed = _numbers(" ".join(excerpts)) | _numbers(question)
    result.unsupported_numbers = sorted(_numbers(body) - allowed)
    if result.unsupported_numbers:
        result.issues.append(f"unsupported_numbers:{','.join(result.unsupported_numbers)}")

    # 3. Unsafe advice: the model must never suggest defeating protections.
    lowered = result.answer.lower()
    if any(re.search(p, lowered) for p in UNSAFE_ADVICE_PATTERNS):
        result.unsafe_advice = True
        result.issues.append("unsafe_advice")
    return result
