"""CLI.

    python -m fleetops.cli ingest
    python -m fleetops.cli ask "Why does R-1007 keep stopping?" --role fleet_manager [--trace]
"""

import argparse
import json
import logging


def main() -> None:
    p = argparse.ArgumentParser(prog="fleetops")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("ingest")
    a = sub.add_parser("ask")
    a.add_argument("question")
    a.add_argument("--role", default=None)
    a.add_argument("--trace", action="store_true")
    a.add_argument("--json", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    from fleetops.config import get_settings
    from fleetops.ingest import build_index, ensure_index

    if args.cmd == "ingest":
        print(build_index())
        return
    ensure_index()
    from fleetops.service import get_assistant

    r = get_assistant().ask(args.question, args.role or get_settings().default_role, "cli")
    if args.json:
        print(json.dumps({k: v for k, v in r.items() if k != "contexts"}, indent=2, default=str))
        return
    print(f"\nRole: {r['role']} | intent: {r['intent'].get('intent')} ({r['intent'].get('method')}) | plan: {r['plan']}")
    print("-" * 78)
    print(r["answer"])
    print(f"\nCitations: {', '.join(r['citations']) or '-'}")
    print(f"outcome={r['outcome']} latency={r['latency_ms']} ms guardrail={r['guardrail']} run_id={r['run_id']}")
    if args.trace:
        print("\nTrace:\n  " + "\n  ".join(r["trace"]))


if __name__ == "__main__":
    main()
