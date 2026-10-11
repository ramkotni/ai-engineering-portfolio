"""Deterministic guardrails for robot operations.

Input : length, prompt injection, SAFETY overrides (disable/bypass e-stop, lidar, bumpers, safety fields,
        driving into restricted / human-only zones), COMMANDS to act on the fleet (dispatch, reassign,
        reboot, push firmware) - the assistant only recommends; the shift lead acts in the fleet console.
Output: numeric grounding, robot-ID / event-ID grounding, unsafe advice.
"""

import re
from dataclasses import dataclass, field

INJECTION_PATTERNS = [
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|all|your)\b.{0,20}\b(instructions?|prompts?|rules?)",
    r"\b(reveal|show|print|repeat)\b.{0,20}\b(system|hidden)\s+(prompt|instructions?)",
    r"\byou are (now|no longer)\b",
    r"\bjailbreak\b|\bdeveloper mode\b",
]
SAFETY_DEVICES = (r"(e-?stops?|emergency stops?|lidar|bumpers?|safety (fields?|scanners?|systems?|stops?|rated)|"
                  r"collision avoidance|speed limits?|protective stops?)")
SAFETY_OVERRIDE = [
    rf"\b(disable|bypass|override|turn off|switch off|mute|ignore|defeat|jumper)\b.{{0,30}}\b{SAFETY_DEVICES}",
    r"\b(drive|send|move|route|force)\b.{0,40}\b(restricted|human[- ]only|pedestrian|no[- ]go)\s+(zones?|areas?)",
]
_COMMAND = r"^(?:please\s+|go ahead and\s+|(?:can|could|would|will) you\s+(?:please\s+)?|i need you to\s+)?"
ACTION_PATTERNS = [
    _COMMAND + r"(dispatch|reassign|assign|move|reboot|restart|shut ?down|power off|deploy|push|roll ?back|update)\b.{0,40}"
    r"\b(robots?|r-\d{4}|tasks?|firmware|fleet)\b",
]
EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")

BLOCK_MESSAGES = {
    "prompt_injection": "I can only help with robot fleet operations. Please rephrase your question.",
    "safety_override": (
        "I can't help disable or bypass robot safety systems or send robots into restricted zones. Put the robot in "
        "maintenance mode from the fleet console and follow RB-GUIDE-001 'Safety Before Any Work'."
    ),
    "action_request": (
        "I'm advisory only: I can recommend dispatch, reassignment or firmware actions, but the shift lead executes "
        "them in the fleet console. Ask me 'what should we reassign?' for a recommendation."
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
    for pattern, label in ((EMAIL, "email"), (PHONE, "phone")):
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
    for cat, patterns in (("prompt_injection", INJECTION_PATTERNS), ("safety_override", SAFETY_OVERRIDE),
                          ("action_request", ACTION_PATTERNS)):
        if any(re.search(p, low) for p in patterns):
            return InputCheck(False, q, cat, BLOCK_MESSAGES[cat], flags)
    return InputCheck(True, q, flags=flags)


NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
IDS = re.compile(r"\b(?:R-\d{4}|RB-EVT-\d{4}|MNT-\d{4})\b")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+", re.MULTILINE)
UNSAFE_ADVICE = [rf"\b(disable|bypass|override|turn off|ignore)\b.{{0,30}}\b{SAFETY_DEVICES}"]


def _norm(n: str) -> str:
    n = n.replace(",", "")
    return (n.rstrip("0").rstrip(".") if "." in n else n) or "0"


def _numbers(text: str) -> set[str]:
    return {_norm(n) for n in NUMBER.findall(IDS.sub(" ", text))}


@dataclass
class OutputCheck:
    answer: str
    issues: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.startswith(("unsupported_numbers", "unknown_ids", "unsafe_advice")) for i in self.issues)


def check_output(answer: str, evidence: str, question: str = "") -> OutputCheck:
    text, flags = redact(answer)
    out = OutputCheck(text, list(flags))
    body = LIST_MARKER.sub(" ", text)
    nums = sorted(_numbers(body) - _numbers(evidence) - _numbers(question))
    if nums:
        out.issues.append("unsupported_numbers:" + ",".join(nums))
    unknown = sorted(set(IDS.findall(text)) - set(IDS.findall(evidence)) - set(IDS.findall(question)))
    if unknown:
        out.issues.append("unknown_ids:" + ",".join(unknown))
    if any(re.search(p, text.lower()) for p in UNSAFE_ADVICE):
        out.issues.append("unsafe_advice")
    return out
