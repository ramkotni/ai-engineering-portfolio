"""SEC EDGAR client (live mode): ticker -> CIK, recent filings, filing documents and XBRL company facts.

SEC fair-access rules: a descriptive User-Agent with contact details (SEC_USER_AGENT in .env) and at most 10
requests per second. Responses are cached in data/cache/ (git-ignored) so repeat briefings do not re-download.
"""

import json
import logging
import time
from pathlib import Path

import httpx

from stockbrief.config import Settings, get_settings

log = logging.getLogger(__name__)
_last_call = [0.0]


class EdgarNotConfigured(RuntimeError):
    pass


def _get(url: str, s: Settings) -> httpx.Response:
    if not s.sec_user_agent.strip():
        raise EdgarNotConfigured("Set SEC_USER_AGENT in .env (e.g. 'Your Company your.name@example.com') to use live SEC data.")
    wait = 0.15 - (time.monotonic() - _last_call[0])      # stay well under 10 requests/second
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.monotonic()
    r = httpx.get(url, headers={"User-Agent": s.sec_user_agent, "Accept-Encoding": "gzip, deflate"}, timeout=s.http_timeout,
                  follow_redirects=True)
    r.raise_for_status()
    return r


def _cached(name: str, url: str, max_age_hours: float, s: Settings, binary: bool = False):
    path: Path = s.cache_dir / name
    if path.exists() and time.time() - path.stat().st_mtime < max_age_hours * 3600:
        return path.read_bytes() if binary else path.read_text(encoding="utf-8")
    r = _get(url, s)
    path.parent.mkdir(parents=True, exist_ok=True)
    if binary:
        path.write_bytes(r.content)
        return r.content
    path.write_text(r.text, encoding="utf-8")
    return r.text


def ticker_map(settings: Settings | None = None) -> dict[str, dict]:
    s = settings or get_settings()
    data = json.loads(_cached("company_tickers.json", f"{s.sec_archive_url}/files/company_tickers.json", 24, s))
    return {v["ticker"].upper(): {"cik": str(v["cik_str"]).zfill(10), "name": v["title"]} for v in data.values()}


def recent_filings(cik: str, forms=("10-K", "10-Q", "8-K"), limit: int = 6, settings: Settings | None = None) -> list[dict]:
    s = settings or get_settings()
    sub = json.loads(_cached(f"submissions_{cik}.json", f"{s.sec_base_url}/submissions/CIK{cik}.json", 6, s))
    r = sub["filings"]["recent"]
    out = []
    for i, form in enumerate(r["form"]):
        if form in forms:
            acc = r["accessionNumber"][i]
            out.append({"form": form, "filed": r["filingDate"][i], "period": r["reportDate"][i], "accession": acc,
                        "primary_document": r["primaryDocument"][i], "description": r["primaryDocDescription"][i],
                        "url": f"{s.sec_archive_url}/Archives/edgar/data/{int(cik)}/{acc.replace('-', '')}/{r['primaryDocument'][i]}"})
        if len(out) >= limit:
            break
    return out


def filing_html(filing: dict, settings: Settings | None = None) -> str:
    s = settings or get_settings()
    raw = _cached(f"docs/{filing['accession']}.htm", filing["url"], 24 * 365, s, binary=True)
    return raw.decode("utf-8", errors="ignore")


def company_facts(cik: str, settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    return json.loads(_cached(f"facts_{cik}.json", f"{s.sec_base_url}/api/xbrl/companyfacts/CIK{cik}.json", 24, s))
