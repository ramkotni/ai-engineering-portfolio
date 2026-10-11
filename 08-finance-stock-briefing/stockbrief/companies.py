"""Resolve what an advisor types ("NWRB", "$HLXB", "Helix Biologics", "MSFT") to a company.

Synthetic mode knows only the two fictional companies; live mode uses the SEC ticker list (10,000+ issuers).
"""

import json
import re
from dataclasses import dataclass

from stockbrief.config import Settings, get_settings

_TICKER = re.compile(r"\$?\b([A-Z]{1,5}(?:\.[A-Z])?)\b")
_STOP = {"I", "A", "AN", "THE", "AND", "OR", "Q", "FY", "EPS", "CEO", "CFO", "SEC", "MD", "USD", "AI", "IS", "IT", "ON", "IN", "OF",
         "FOR", "TO", "ME", "MY", "WHAT", "WHY", "HOW", "DOES", "DO", "ITS", "GIVE", "BRIEF", "STOCK", "RISK", "K", "PE"}


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    cik: str
    source: str            # synthetic | live
    sector: str = ""
    industry: str = ""


def synthetic_catalogue(settings: Settings | None = None) -> dict[str, Company]:
    s = settings or get_settings()
    data = json.loads((s.data_dir / "companies.json").read_text(encoding="utf-8"))
    return {t: Company(t, c["name"], c["cik"], "synthetic", c["sector"], c["industry"]) for t, c in data.items()}


def resolve(text: str, source: str, settings: Settings | None = None) -> Company | None:
    s = settings or get_settings()
    if source == "live":
        from stockbrief.edgar import ticker_map

        universe = {t: Company(t, v["name"], v["cik"], "live") for t, v in ticker_map(s).items()}
    else:
        universe = synthetic_catalogue(s)
    for cand in _TICKER.findall(text):
        if cand not in _STOP and cand in universe:
            return universe[cand]
    low = " " + re.sub(r"[^a-z0-9 ]", " ", text.lower()) + " "
    named = [c for c in universe.values() if _core(c.name) and f" {_core(c.name)} " in low]
    if not named and source != "live":      # small catalogue: the distinctive first word is enough ("Helix's cash")
        named = [c for c in universe.values() if f" {_core(c.name).split()[0]} " in low or f" {_core(c.name).split()[0]}s " in low]
    return min(named, key=lambda c: len(c.name)) if named else None


def _core(name: str) -> str:
    """'Helix Biologics Corp.' -> 'helix biologics' (drop legal suffixes for name matching)."""
    words = re.sub(r"[^a-z0-9 ]", " ", name.lower()).split()
    while words and words[-1] in ("inc", "corp", "corporation", "co", "ltd", "plc", "company", "holdings", "group", "the", "sa", "nv", "ag"):
        words.pop()
    return " ".join(words)
