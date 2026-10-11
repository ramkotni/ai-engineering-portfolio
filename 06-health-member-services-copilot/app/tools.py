"""Claims tool used by the Claims agent.

Production note: this would call the claims system of record (REST API /
DynamoDB). The key design point is *tool-level authorization*: the agent can
only read claims owned by the authenticated member, no matter what the LLM or
the user asks for. Authorization is never delegated to the model.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

CLAIM_ID_RE = re.compile(r"\bCLM-?\s?(\d{5})\b", re.IGNORECASE)


def extract_claim_id(text: str) -> str | None:
    m = CLAIM_ID_RE.search(text or "")
    return f"CLM-{m.group(1)}" if m else None


@dataclass
class ClaimLookup:
    found: bool
    authorized: bool
    claim: dict | None = None
    message: str = ""


class ClaimsRepository:
    def __init__(self, claims_file: Path):
        self._claims = {c["claim_id"]: c for c in json.loads(Path(claims_file).read_text(encoding="utf-8"))}

    def get_claim(self, claim_id: str, member_id: str | None) -> ClaimLookup:
        claim = self._claims.get(claim_id.upper())
        if member_id is None:
            return ClaimLookup(False, False, message="You need to be signed in to look up claims.")
        # Same response for "not found" and "not yours" -> no claim-ID enumeration.
        if claim is None or claim["member_id"] != member_id:
            return ClaimLookup(False, claim is None, message=f"I couldn't find claim {claim_id} on your account.")
        return ClaimLookup(True, True, claim=claim)

    def list_claims(self, member_id: str) -> list[dict]:
        return [c for c in self._claims.values() if c["member_id"] == member_id]
