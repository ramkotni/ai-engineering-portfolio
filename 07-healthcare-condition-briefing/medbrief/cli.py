"""Command line.

    python -m medbrief.cli brief "heart failure" --role strategy_analyst [--live] [--trace]
    python -m medbrief.cli ask "What does Figure 1 recommend after 3 months of GDMT?" --role clinical_advisor
"""

import argparse
import logging


def main() -> None:
    ap = argparse.ArgumentParser(description="Condition Briefing Assistant")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("brief")
    b.add_argument("condition")
    b.add_argument("--live", action="store_true", help="live trial data from ClinicalTrials.gov")
    q = sub.add_parser("ask")
    q.add_argument("question")
    for p in (b, q):
        p.add_argument("--role", default="strategy_analyst")
        p.add_argument("--trace", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING)

    from medbrief.ingest import ensure_index
    from medbrief.service import get_service

    ensure_index()
    svc = get_service()
    r = (svc.brief(args.condition, args.role, "live" if args.live else "synthetic", "cli") if args.cmd == "brief"
         else svc.ask(args.question, args.role, "cli"))
    print(r["answer"])
    print(f"\n[outcome={r['outcome']} latency={r['latency_ms'] / 1000:.1f}s guardrail={r['guardrail']}]")
    if args.trace:
        print("\n".join(r["trace"]))


if __name__ == "__main__":
    main()
