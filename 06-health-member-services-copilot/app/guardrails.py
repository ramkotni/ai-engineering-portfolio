"""Layered guardrails (defense in depth).

Layer 1 - Edge:   PII redaction before anything is logged, stored, or sent to an LLM.
Layer 2 - Input:  size limits, prompt-injection / jailbreak heuristics,
                  optional Amazon Bedrock Guardrails (content, denied topics,
                  prompt-attack filter) via the ApplyGuardrail API.
Layer 3 - Tool:   authorization enforced in code (see app/tools.py).
Layer 4 - Output: groundedness critic (graph node), PII leak prevention,
                  optional Bedrock contextual-grounding check.

Local rules are deterministic, fast and free; the managed Bedrock guardrail
adds ML-based classifiers. Either layer can block.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------- PII -------
PII_PATTERNS: dict[str, re.Pattern] = {
    "SSN": re.compile(r"\b(?!000|666|9\d\d)\d{3}[- ]?(?!00)\d{2}[- ]?(?!0000)\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    "PHONE": re.compile(r"(?<!\w)(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b"),
    # Contextual: only dates introduced as a birth date (service dates in claims must stay readable).
    "DOB": re.compile(r"(?:dob|date of birth|born on)\W{0,3}(?:is\s+)?(?P<v>\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", re.IGNORECASE),
}


def _luhn_ok(number: str) -> bool:
    digits = [int(d) for d in re.sub(r"\D", "", number)]
    if not 13 <= len(digits) <= 16:
        return False
    checksum = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


def find_pii(text: str) -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for kind, pattern in PII_PATTERNS.items():
        for m in pattern.finditer(text or ""):
            value = m.group("v") if "v" in pattern.groupindex else m.group(0)
            if kind == "CREDIT_CARD" and not _luhn_ok(value):
                continue
            hits.append((kind, value))
    return hits


def redact_pii(text: str, allow: set[str] | None = None) -> tuple[str, list[str]]:
    """Replace PII with typed placeholders. Values in `allow` are kept
    (e.g. official phone numbers that appear in the retrieved policy docs)."""
    allow = allow or set()
    found: list[str] = []
    for kind, value in find_pii(text):
        if value in allow:
            continue
        text = text.replace(value, f"[REDACTED_{kind}]")
        found.append(kind)
    return text, sorted(set(found))


# ---------------------------------------------------- Prompt injection ------
INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts|rules)",
    r"disregard (your|all|the) (instructions|rules|guidelines)",
    r"(reveal|show|print|repeat) (me )?(your|the) (system|hidden|initial) (prompt|instructions)",
    r"you are now (an? |in )?(dan|unrestricted|unfiltered|jailbroken|evil|developer|free from)",
    r"forget (everything|all|your) (you were told|(previous |prior )?instructions|rules)",
    r"\b(developer|dan|god) mode\b",
    r"\bjailbreak\b",
    r"pretend (you are|to be) (not|an? unrestricted)",
    r"act as (an? )?(unrestricted|unfiltered)",
    r"</?(system|assistant)>",
    r"show (me )?(all|every|other) (members?|users?)('s|')? (claims|data|records)",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


def detect_prompt_injection(text: str) -> str | None:
    m = _INJECTION_RE.search(text or "")
    return m.group(0) if m else None


# ---------------------------------------------------------- Results ---------
@dataclass
class GuardrailResult:
    blocked: bool = False
    reason: str | None = None
    flags: list[str] = field(default_factory=list)
    text: str = ""

    def to_dict(self) -> dict:
        return {"blocked": self.blocked, "reason": self.reason, "flags": self.flags}


BLOCKED_MESSAGE = (
    "I'm sorry, I can't help with that request. I can answer questions about your "
    "Evergreen plan benefits, claims, prior authorization, pharmacy coverage, and appeals."
)


# --------------------------------------------- Amazon Bedrock Guardrails ----
class BedrockGuardrail:
    """Wrapper over the Bedrock ApplyGuardrail API (works with ANY model, incl. Ollama)."""

    def __init__(self, settings: Settings):
        import boto3

        self.s = settings
        self.client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def check(self, text: str, source: str, grounding_source: str | None = None, query: str | None = None) -> GuardrailResult:
        content: list[dict] = []
        if grounding_source:
            content.append({"text": {"text": grounding_source[:50000], "qualifiers": ["grounding_source"]}})
            if query:
                content.append({"text": {"text": query, "qualifiers": ["query"]}})
            content.append({"text": {"text": text, "qualifiers": ["guard_content"]}})
        else:
            content.append({"text": {"text": text}})
        try:
            resp = self.client.apply_guardrail(
                guardrailIdentifier=self.s.bedrock_guardrail_id,
                guardrailVersion=self.s.bedrock_guardrail_version,
                source=source,
                content=content,
            )
        except Exception as exc:  # network / throttling / permissions
            logger.error("bedrock guardrail unavailable: %s", exc)
            if self.s.guardrail_fail_closed:
                return GuardrailResult(True, "guardrail_unavailable", ["bedrock_error"], text)
            return GuardrailResult(False, None, ["bedrock_error_fail_open"], text)

        if resp.get("action") == "GUARDRAIL_INTERVENED":
            outputs = resp.get("outputs") or []
            masked = outputs[0]["text"] if outputs else BLOCKED_MESSAGE
            # Distinguish "masked PII but allowed" from a hard block.
            policies = _intervening_policies(resp)
            hard_block = any(p != "sensitiveInformationPolicy" for p in policies) or not outputs
            return GuardrailResult(hard_block, f"bedrock:{','.join(policies) or 'intervened'}", [f"bedrock:{p}" for p in policies], masked)
        return GuardrailResult(False, None, [], text)


def _intervening_policies(resp: dict) -> list[str]:
    names = set()
    for assessment in resp.get("assessments", []):
        for key, val in assessment.items():
            if val and key.endswith("Policy"):
                names.add(key)
    return sorted(names)


# ------------------------------------------------------------ Facade --------
class Guardrails:
    def __init__(self, settings: Settings | None = None, bedrock: BedrockGuardrail | None = None):
        self.s = settings or get_settings()
        self.bedrock = bedrock
        if self.bedrock is None and self.s.bedrock_guardrail_id:
            self.bedrock = BedrockGuardrail(self.s)

    def sanitize(self, text: str) -> GuardrailResult:
        """Edge layer: redact PII before the text enters the system."""
        clean, kinds = redact_pii(text)
        return GuardrailResult(False, None, [f"pii_redacted:{k}" for k in kinds], clean)

    def check_input(self, text: str) -> GuardrailResult:
        if not text or not text.strip():
            return GuardrailResult(True, "empty_input", ["empty"], text)
        if len(text) > self.s.max_input_chars:
            return GuardrailResult(True, "input_too_long", ["length"], text)
        hit = detect_prompt_injection(text)
        if hit:
            return GuardrailResult(True, "prompt_injection", [f"injection:{hit.lower()}"], text)
        if self.bedrock:
            return self.bedrock.check(text, source="INPUT")
        return GuardrailResult(False, None, [], text)

    def check_output(self, answer: str, context: str = "", query: str = "") -> GuardrailResult:
        # Allow PII-like strings that legitimately come from source docs (official phone numbers).
        allowed = {v for _, v in find_pii(context)} | set(self.s.pii_allowlist)
        clean, kinds = redact_pii(answer, allow=allowed)
        flags = [f"output_pii_redacted:{k}" for k in kinds]
        if self.bedrock:
            res = self.bedrock.check(clean, source="OUTPUT", grounding_source=context or None, query=query or None)
            res.flags = flags + res.flags
            return res
        return GuardrailResult(False, None, flags, clean)
