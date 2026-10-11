"""Guardrail red-team suite. Instant: no LLM, no network (local rules only by default).

    python -m eval.guardrail_check              # local rules
    python -m eval.guardrail_check --bedrock    # + Amazon Bedrock Guardrails (needs BEDROCK_GUARDRAIL_ID + AWS creds)

Categories: injection (should block), pii (should redact the right types),
benign (must NOT block or redact: false-positive checks), length, authz (tool-level).
Cases marked `known_gap` document what regex rules cannot catch; they are
reported separately and don't fail the run. Every other case must pass (exit 1).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.config import PROJECT_ROOT, get_settings
from app.guardrails import Guardrails
from app.tools import ClaimsRepository

HERE = Path(__file__).parent
SUITE = HERE / "guardrail_redteam.jsonl"
REPORTS = HERE / "reports"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in SUITE.read_text(encoding="utf-8").splitlines() if line.strip()]


def case_input(case: dict) -> str:
    return "a" * case["repeat"] if case.get("repeat") else case.get("input", "")


def run_case(case: dict, guardrails: Guardrails, repo: ClaimsRepository, results_by_id: dict | None = None) -> dict:
    """Returns {"passed": bool, "detail": str}."""
    if case["category"] == "authz":
        lookup = repo.get_claim(case["claim_id"], case["member_id"])
        ok = lookup.found == case["expect_access"]
        detail = f"access={lookup.found} msg={lookup.message!r}"
        ref = (results_by_id or {}).get(case.get("same_message_as", ""))
        if ok and ref is not None:  # no enumeration: 'missing' and 'not yours' must look identical
            ok = lookup.message.replace(case["claim_id"], "{id}") == ref["message"].replace(ref["claim_id"], "{id}")
            detail += " | same message as " + case["same_message_as"] + f": {ok}"
        return {"passed": ok, "detail": detail, "message": lookup.message, "claim_id": case["claim_id"]}

    text = case_input(case)
    sanitized = guardrails.sanitize(text)
    found_pii = sorted(f.split(":", 1)[1] for f in sanitized.flags if f.startswith("pii_redacted:"))
    check = guardrails.check_input(sanitized.text)
    checks = []
    if "expect_block" in case:
        checks.append(check.blocked == case["expect_block"])
    if "expect_pii" in case:
        checks.append(set(found_pii) == set(case["expect_pii"]))
    detail = f"blocked={check.blocked} reason={check.reason} pii={found_pii}"
    return {"passed": all(checks), "detail": detail}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--bedrock", action="store_true", help="include Amazon Bedrock Guardrails (ApplyGuardrail)")
    p.add_argument("--out", default="guardrails_latest", help="report file stem in eval/reports/")
    args = p.parse_args()

    s = get_settings()
    if not args.bedrock:
        s = s.model_copy(update={"bedrock_guardrail_id": None})
    guardrails = Guardrails(s)
    repo = ClaimsRepository(PROJECT_ROOT / "data" / "claims" / "claims.json")

    results, by_id = [], {}
    for case in load_cases():
        r = run_case(case, guardrails, repo, by_id)
        by_id[case["id"]] = r
        results.append({"id": case["id"], "category": case["category"], "known_gap": case.get("known_gap"), **r})

    must = [r for r in results if not r["known_gap"]]
    gaps = [r for r in results if r["known_gap"]]
    per_cat = Counter(r["category"] for r in must)
    per_cat_pass = Counter(r["category"] for r in must if r["passed"])
    summary = {
        "mode": "local+bedrock" if args.bedrock else "local rules",
        "must_pass": f"{sum(r['passed'] for r in must)}/{len(must)}",
        "by_category": {c: f"{per_cat_pass[c]}/{n}" for c, n in per_cat.items()},
        "known_gaps_open": [r["id"] for r in gaps if not r["passed"]],
        "known_gaps_now_covered": [r["id"] for r in gaps if r["passed"]],
        "failures": [r["id"] for r in must if not r["passed"]],
    }

    print(f"{'id':8} {'category':10} {'result':8} detail")
    for r in results:
        status = ("PASS" if r["passed"] else "FAIL") if not r["known_gap"] else ("covered" if r["passed"] else "gap")
        print(f"{r['id']:8} {r['category']:10} {status:8} {r['detail'][:90]}")
    print("\n" + json.dumps(summary, indent=2))

    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{args.out}.json").write_text(
        json.dumps({"timestamp": datetime.now().isoformat(), "summary": summary, "results": results}, indent=2), encoding="utf-8")
    return 0 if not summary["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
