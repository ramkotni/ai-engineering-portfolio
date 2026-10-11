"""Runs the red-team suite (eval/guardrail_redteam.jsonl) as tests.
Known gaps (regex can't catch them; Bedrock PROMPT_ATTACK / NER can) are xfail, not hidden."""
import pytest

from app.config import PROJECT_ROOT
from app.guardrails import Guardrails
from app.tools import ClaimsRepository
from eval.guardrail_check import load_cases, run_case

CASES = load_cases()
BY_ID = {c["id"]: c for c in CASES}


@pytest.fixture(scope="module")
def deps():
    from app.config import Settings

    s = Settings(_env_file=None, bedrock_guardrail_id=None)
    return Guardrails(s), ClaimsRepository(PROJECT_ROOT / "data" / "claims" / "claims.json")


def _params():
    for c in CASES:
        marks = [pytest.mark.xfail(reason=c["known_gap"], strict=False)] if c.get("known_gap") else []
        yield pytest.param(c, id=c["id"], marks=marks)


@pytest.mark.parametrize("case", _params())
def test_redteam_case(case, deps):
    guardrails, repo = deps
    refs = {}
    if case.get("same_message_as"):
        ref_case = BY_ID[case["same_message_as"]]
        refs[ref_case["id"]] = run_case(ref_case, guardrails, repo)
    result = run_case(case, guardrails, repo, refs)
    assert result["passed"], result["detail"]
