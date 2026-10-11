"""Command line.

    python -m stockbrief.cli brief NWRB --role financial_advisor [--live] [--trace]
    python -m stockbrief.cli quote MSFT --live
    python -m stockbrief.cli ask "What does HLXB say about its cash runway?"
"""

import argparse
import logging


def main() -> None:
    ap = argparse.ArgumentParser(description="Stock Briefing Assistant")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("brief", "quote", "ask"):
        p = sub.add_parser(name)
        p.add_argument("text", help="ticker / company name, or the question for 'ask'")
        p.add_argument("--role", default="financial_advisor")
        p.add_argument("--live", action="store_true", help="live quotes (Yahoo Finance) and SEC EDGAR filings")
        p.add_argument("--trace", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    from stockbrief.ingest import ensure_index
    from stockbrief.service import get_service

    ensure_index()
    svc = get_service()
    source = "live" if args.live else "synthetic"
    r = {"brief": svc.brief, "quote": svc.quote, "ask": svc.ask}[args.cmd](args.text, args.role, source, "cli")
    print(r["answer"])
    print(f"\n[outcome={r['outcome']} latency={r['latency_ms'] / 1000:.1f}s guardrail={r['guardrail']}]")
    if args.trace:
        print("\n".join(r["trace"]))


if __name__ == "__main__":
    main()
