"""Deterministic guardrails for an advisor-facing research tool (informational, not a recommendation engine).

Input : length, prompt injection, investment advice requests (buy/sell/hold, price targets, allocations - those go
        through the firm's research and suitability process), material non-public information, PII redaction
        (account numbers, SSN, email, phone).
Output: numeric grounding (every number must appear in the evidence: filings, computed quote and financial
        metrics), recommendation language is REMOVED (bullets with buy/sell/hold, price targets, "undervalued"),
        PII redaction, and a disclaimer with data timestamps is always attached.
"""

import re
from dataclasses import dataclass, field

INJECTION = [
    r"\b(ignore|disregard|forget)\b.{0,30}\b(previous|prior|above|all|your)\b.{0,20}\b(instructions?|prompts?|rules?)",
    r"\b(reveal|show|print|repeat)\b.{0,20}\b(system|hidden)\s+(prompt|instructions?)",
    r"\byou are (now|no longer)\b",
    r"\bjailbreak\b|\bdeveloper mode\b",
]
ADVICE = [
    r"\bshould\s+(i|we|my client|the client|they)\s+(buy|sell|hold|short|invest|add|trim|exit)\b",
    r"\b(buy|sell|hold)\s+or\s+(buy|sell|hold)\b",
    r"\bprice target\b|\btarget price\b",
    r"\bis\s+(it|\w{1,5})\s+(a\s+)?(good|bad|great|safe)\s+(buy|investment|stock to buy)\b",
    r"\bwill\s+(the\s+)?(stock|shares|price|it|\w{1,5})\s+(go|move)\s+(up|down|higher|lower)\b",
    r"\bhow much\b.{0,30}\b(invest|allocate|put)\b",
    r"\b(recommend|suggest)\b.{0,20}\b(buying|selling|shorting|position)\b",
    r"\b(undervalued|overvalued)\b\s*\?",
]
MNPI = [r"\b(insider|non-?public|confidential)\s+(information|info|tip|data)\b", r"\bbefore\s+(it'?s|it is|they are)\s+(announced|public|released)\b",
        r"\bleak(ed)?\b.{0,20}\b(earnings|results|deal)\b"]
PII = [(re.compile(r"\b(?:acct|account)\s*(?:no\.?|number|#)?\s*[:#]?\s*\d{6,12}\b", re.IGNORECASE), "account"),
       (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "ssn"),
       (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "email"),
       (re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)"), "phone")]
MESSAGES = {
    "prompt_injection": "I can only brief from market data and public filings. Please rephrase your request.",
    "investment_advice": "I can't give buy, sell or hold recommendations, price targets or allocation advice. I summarise market data "
                         "and SEC filings; recommendations must follow the firm's research and suitability process.",
    "mnpi": "I only use public information (market data and SEC filings). Material non-public information must be reported to Compliance.",
    "too_long": "Please keep the request under {max} characters.",
}
DISCLAIMER = ("For internal advisor preparation only. Summarises public filings and market data; not investment advice or a "
              "recommendation. Verify figures against the source filings before sharing with clients.")
ADVICE_OUT = re.compile(r"\b(strong\s+)?(buy|sell|hold)\s+(rating|recommendation)\b|\bwe\s+recommend\b|\bprice target\b|\btarget price\b|"
                        r"\b(undervalued|overvalued)\b|\b(investors|clients|you)\s+should\s+(buy|sell|hold|consider buying|consider selling)\b",
                        re.IGNORECASE)


@dataclass
class InputCheck:
    allowed: bool
    text: str
    category: str | None = None
    message: str | None = None
    flags: list[str] = field(default_factory=list)


def redact(text: str) -> tuple[str, list[str]]:
    flags = []
    for pattern, label in PII:
        if pattern.search(text):
            text, flags = pattern.sub(f"[{label}]", text), flags + [f"redacted_{label}"]
    return text, flags


def check_input(text: str, max_chars: int = 1000) -> InputCheck:
    t = " ".join(text.split())
    if len(t) > max_chars:
        return InputCheck(False, t[:max_chars], "too_long", MESSAGES["too_long"].format(max=max_chars))
    t, flags = redact(t)
    low = t.lower()
    for cat, patterns in (("prompt_injection", INJECTION), ("mnpi", MNPI), ("investment_advice", ADVICE)):
        if any(re.search(p, low) for p in patterns):
            return InputCheck(False, t, cat, MESSAGES[cat], flags)
    return InputCheck(True, t, flags=flags)


NUMBER = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w])")
CITE = re.compile(r"\[\d+(?:\s*,\s*\d+)*\]")
LIST_MARKER = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+", re.MULTILINE)
FORMS = re.compile(r"\b(?:10-K|10-Q|8-K|Item\s+\d+[A-C]?)\b", re.IGNORECASE)


def _norm(n: str) -> str:
    n = n.replace(",", "")
    return (n.rstrip("0").rstrip(".") if "." in n else n) or "0"


def _numbers(text: str) -> set[str]:
    return {_norm(n) for n in NUMBER.findall(FORMS.sub(" ", CITE.sub(" ", text)))}


@dataclass
class OutputCheck:
    sections: dict[str, list[str]]
    issues: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.startswith("unsupported_numbers") for i in self.issues)


def compliance_review(sections: dict[str, list[str]], evidence: str, request: str = "") -> OutputCheck:
    """Removes recommendation language bullet by bullet, redacts PII, checks every number against the evidence."""
    clean: dict[str, list[str]] = {}
    out = OutputCheck(clean)
    allowed = _numbers(evidence) | _numbers(request)
    for heading, bullets in sections.items():
        kept = []
        for b in bullets:
            b, flags = redact(b)
            out.issues += flags
            if ADVICE_OUT.search(b):
                out.removed.append(b)
                continue
            kept.append(b)
        clean[heading] = kept
    if out.removed:
        out.issues.append(f"advice_language_removed:{len(out.removed)}")
    text = "\n".join(LIST_MARKER.sub(" ", b) for v in clean.values() for b in v)
    nums = sorted(_numbers(text) - allowed)
    if nums:
        out.issues.append("unsupported_numbers:" + ",".join(nums))
    return out


def check_answer(answer: str, evidence: str, request: str = "") -> list[str]:
    text, flags = redact(answer)
    issues = list(flags)
    nums = sorted(_numbers(LIST_MARKER.sub(" ", text)) - _numbers(evidence) - _numbers(request))
    if nums:
        issues.append("unsupported_numbers:" + ",".join(nums))
    if ADVICE_OUT.search(text):
        issues.append("advice_language")
    return issues
