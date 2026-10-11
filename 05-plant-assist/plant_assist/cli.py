"""Command-line interface.

    python -m plant_assist.cli ingest
    python -m plant_assist.cli ask "How do I clear a jam on CV-3?" [--trace] [--json]
    python -m plant_assist.cli chat
"""

import argparse
import json
import logging


def _print_result(result: dict, show_trace: bool) -> None:
    route = result["route"]
    print(f"\nRoute: {route.get('primary_source')} (+{route.get('secondary_sources')}) "
          f"conf={route.get('confidence', 0):.2f} via {route.get('method')} | searched {result['searched_sources']}")
    print("-" * 78)
    print(result["answer"])
    if result["citations"]:
        print("\nSources:")
        for c in result["citations"]:
            print(f"  [{c['ref']}] {c['doc_id']} rev {c['revision']} - {c['title']} > {c['section']}")
    print(f"\noutcome={result['outcome']} grounded={result['grounded']} latency={result['latency_ms']} ms")
    print(f"guardrails={result['guardrail']} run_id={result['run_id']}")
    if show_trace:
        print("\nTrace:")
        for line in result["trace"]:
            print(f"  - {line}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="plant-assist")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("ingest", help="(re)build the vector index from data/docs")
    ask = sub.add_parser("ask", help="ask one question")
    ask.add_argument("question")
    ask.add_argument("--trace", action="store_true", help="show the graph execution trace")
    ask.add_argument("--json", action="store_true", help="print the raw JSON result")
    chat = sub.add_parser("chat", help="interactive session")
    chat.add_argument("--trace", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    from plant_assist.ingest import build_index, ensure_index

    if args.command == "ingest":
        print(f"Indexed chunks per source: {build_index(reset=True)}")
        return

    ensure_index()
    from plant_assist.service import get_assistant

    assistant = get_assistant()
    if args.command == "ask":
        result = assistant.ask(args.question, channel="cli")
        print(json.dumps(result, indent=2)) if args.json else _print_result(result, args.trace)
        return

    print("PlantAssist - ask about safety, maintenance or quality. Type 'exit' to quit.")
    while True:
        try:
            question = input("\nsupervisor> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if question.lower() in {"exit", "quit"}:
            break
        if question:
            _print_result(assistant.ask(question, channel="cli"), args.trace)


if __name__ == "__main__":
    main()
