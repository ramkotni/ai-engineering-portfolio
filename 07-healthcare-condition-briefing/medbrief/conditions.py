"""Condition catalogue: maps what a user types ("CHF", "type 2 diabetes") to a condition, its guideline documents,
its rows in the synthetic registry and its ClinicalTrials.gov search term.

A condition that is not in the catalogue can still be briefed in live mode: emerging treatments and key players
come from ClinicalTrials.gov, and the standard-of-care section says that no guideline is in the knowledge base.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Condition:
    key: str
    name: str
    short: str
    synonyms: tuple[str, ...]
    guideline_docs: tuple[str, ...]
    registry_condition: str | None
    live_query: str

    @property
    def in_catalogue(self) -> bool:
        return bool(self.guideline_docs)


CATALOGUE = {
    "hfref": Condition("hfref", "Heart failure with reduced ejection fraction (HFrEF)", "HFrEF",
                       ("hfref", "heart failure with reduced ejection fraction", "heart failure", "chf", "congestive heart failure",
                        "systolic heart failure", "reduced ejection fraction"),
                       ("CARD-GL-2026",), "HFrEF", "heart failure with reduced ejection fraction"),
    "t2d": Condition("t2d", "Type 2 diabetes", "T2D",
                     ("type 2 diabetes", "type ii diabetes", "t2d", "t2dm", "diabetes mellitus type 2", "type 2 diabetes mellitus", "diabetes"),
                     ("DM-GL-2026",), "Type 2 diabetes", "type 2 diabetes"),
}


def resolve(text: str) -> Condition | None:
    """Longest synonym found as a whole phrase wins ("heart failure" beats "hf")."""
    low = " " + re.sub(r"[^a-z0-9]+", " ", text.lower()) + " "
    best: tuple[int, Condition] | None = None
    for cond in CATALOGUE.values():
        for syn in cond.synonyms:
            if f" {syn} " in low and (best is None or len(syn) > best[0]):
                best = (len(syn), cond)
    return best[1] if best else None


def adhoc(text: str) -> Condition:
    """A condition outside the catalogue (live mode only)."""
    name = " ".join(text.split())[:80]
    return Condition("adhoc", name, name, (), (), None, name)


def tag_condition(text: str) -> str:
    """Condition tag for a chunk of a multi-condition document (e.g. the strategy brief): 'hfref', 't2d' or 'all'."""
    cond = resolve(text)
    return cond.key if cond else "all"
