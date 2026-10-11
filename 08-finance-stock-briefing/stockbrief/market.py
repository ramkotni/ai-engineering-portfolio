"""Quote data and price metrics.

  synthetic  data/raw/quotes.json (fictional NWRB / HLXB snapshot + 52 weekly closes)
  live       Yahoo Finance chart API (no key; quotes may be delayed). Two calls: 5 days of daily bars for the quote,
             1 year of weekly bars for the trend.

Every derived number (change, % change, position in the 52-week range, 1-year return, market cap, P/E) is computed
here, so the LLM never does arithmetic.
"""

import json
from datetime import UTC, datetime

import httpx

from stockbrief.config import Settings, get_settings

YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0 (stock-briefing-demo)"}


def synthetic_quote(ticker: str, settings: Settings | None = None) -> dict | None:
    s = settings or get_settings()
    return json.loads((s.data_dir / "quotes.json").read_text(encoding="utf-8")).get(ticker.upper())


def live_quote(ticker: str, settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    daily = httpx.get(f"{s.quote_url}/{ticker}", params={"range": "5d", "interval": "1d"}, headers=YAHOO_HEADERS, timeout=s.http_timeout)
    daily.raise_for_status()
    res = daily.json()["chart"]["result"][0]
    meta = res["meta"]
    closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
    weekly = httpx.get(f"{s.quote_url}/{ticker}", params={"range": "1y", "interval": "1wk"}, headers=YAHOO_HEADERS, timeout=s.http_timeout)
    weekly.raise_for_status()
    w = weekly.json()["chart"]["result"][0]
    series = [{"date": datetime.fromtimestamp(ts, UTC).date().isoformat(), "close": round(c, 2)}
              for ts, c in zip(w["timestamp"], w["indicators"]["quote"][0]["close"]) if c is not None]
    return {"symbol": meta["symbol"], "name": meta.get("longName") or meta.get("shortName") or ticker, "currency": meta.get("currency", "USD"),
            "exchange": meta.get("fullExchangeName") or meta.get("exchangeName", ""),
            "as_of": datetime.fromtimestamp(meta["regularMarketTime"], UTC).isoformat(timespec="minutes"),
            "price": meta["regularMarketPrice"], "previous_close": closes[-2] if len(closes) > 1 else meta.get("chartPreviousClose"),
            "day_low": meta.get("regularMarketDayLow"), "day_high": meta.get("regularMarketDayHigh"),
            "fifty_two_week_low": meta.get("fiftyTwoWeekLow"), "fifty_two_week_high": meta.get("fiftyTwoWeekHigh"),
            "volume": meta.get("regularMarketVolume"), "avg_volume": None, "shares_outstanding_m": None,
            "weekly_closes": series, "source": "Yahoo Finance (may be delayed)"}


def price_metrics(q: dict, eps_fy: float | None, shares_m: float | None) -> dict:
    """Derived quote metrics, rounded for display - the same numbers go to the LLM and the UI."""
    price, prev = q["price"], q.get("previous_close")
    low, high = q.get("fifty_two_week_low"), q.get("fifty_two_week_high")
    first = q["weekly_closes"][0]["close"] if q.get("weekly_closes") else None
    shares = q.get("shares_outstanding_m") or shares_m
    return {
        "price": round(price, 2),
        "change": round(price - prev, 2) if prev else None,
        "change_pct": round((price / prev - 1) * 100, 2) if prev else None,
        "range_position_pct": round((price - low) / (high - low) * 100, 1) if low is not None and high and high > low else None,
        "one_year_return_pct": round((price / first - 1) * 100, 1) if first else None,
        "market_cap_bn": round(price * shares / 1000, 2) if shares else None,
        "pe_fy": round(price / eps_fy, 1) if eps_fy and eps_fy > 0 else None,
        "pe_note": None if eps_fy and eps_fy > 0 else "not meaningful (loss-making)" if eps_fy is not None else "EPS unavailable",
    }


def get_quote(ticker: str, source: str, settings: Settings | None = None) -> dict | None:
    return live_quote(ticker, settings) if source == "live" else synthetic_quote(ticker, settings)
