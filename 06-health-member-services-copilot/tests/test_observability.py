"""LangSmith integration tests. No network: tracing stays off or the client is mocked."""
import pytest
from fastapi.testclient import TestClient

from app import observability as obs
from app.config import Settings
from app.service import ChatRequest
from eval.langsmith_eval import deterministic_metrics, to_example

LS_VARS = ("LANGSMITH_TRACING", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "LANGSMITH_ENDPOINT",
           "LANGSMITH_HIDE_INPUTS", "LANGSMITH_HIDE_OUTPUTS")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for v in LS_VARS:  # monkeypatch restores these after each test
        monkeypatch.setenv(v, "placeholder")
        monkeypatch.delenv(v)


def test_tracing_off_by_default():
    assert obs.configure_tracing(Settings(_env_file=None)) is False
    assert not obs.tracing_enabled()


def test_tracing_requires_api_key():
    assert obs.configure_tracing(Settings(_env_file=None, langsmith_tracing=True)) is False


def test_tracing_exports_settings_to_environ():
    import os

    s = Settings(_env_file=None, langsmith_tracing=True, langsmith_api_key="lsv2_test", langsmith_project="demo")
    assert obs.configure_tracing(s) is True
    assert os.environ["LANGSMITH_TRACING"] == "true" and os.environ["LANGSMITH_PROJECT"] == "demo"
    assert obs.tracing_enabled()


def test_run_config_labels_trace_without_raw_member_id():
    cfg = obs.run_config(Settings(_env_file=None), "sess-1", "M1001", "run-123")
    assert cfg["run_id"] == "run-123" and cfg["run_name"] == "member_assist_turn"
    assert cfg["metadata"]["session_id"] == "sess-1"  # LangSmith thread grouping
    assert "M1001" not in str(cfg)  # only a hash leaves the process
    assert cfg["metadata"]["member_hash"] == obs.member_hash("M1001")


def test_automatic_feedback_keys():
    fb = dict((k, s) for k, s, _ in obs.automatic_feedback({"blocked": False, "flags": ["tool_authz_denied"]}, True, "claim_status"))
    assert fb == {"guardrail_blocked": 0.0, "grounded": 1.0, "authz_denied": 1.0, "intent:claim_status": 1.0}


def test_feedback_is_noop_when_tracing_disabled():
    assert obs.submit_user_feedback("run-1", 1.0) is False


def test_response_carries_run_id(service):
    r = service.ask(ChatRequest(question="What is the deductible?", member_id="M1001"))
    assert r.run_id and len(r.run_id) == 36


def test_feedback_endpoint(service, monkeypatch):
    from app import api

    api.app.state.service = service
    with TestClient(api.app) as c:
        assert c.post("/feedback", json={"run_id": "r1", "score": 1}).status_code == 503  # tracing off
        monkeypatch.setattr(api, "submit_user_feedback", lambda *a, **k: True)
        assert c.post("/feedback", json={"run_id": "r1", "score": 0, "comment": "wrong copay"}).status_code == 202
        assert c.post("/feedback", json={"run_id": "r1", "score": 5}).status_code == 422


def test_langsmith_evaluator_matches_local_scoring():
    case = {"id": "pol-01", "category": "policy_question", "question": "Gold PPO deductible?", "member_id": "M1001",
            "expected_intent": "policy_question", "expected_sources": ["01_gold_ppo_benefits.md"], "expected_keywords": ["$500", "$1,000"]}
    ex = to_example(case)
    assert ex["inputs"] == {"question": "Gold PPO deductible?", "member_id": "M1001"}
    out = {"answer": "It is $500 individual.", "intent": "policy_question", "blocked": False, "flags": [],
           "retrieved_sources": ["01_gold_ppo_benefits.md"]}
    scores = {r["key"]: r["score"] for r in deterministic_metrics(ex["inputs"], out, ex["outputs"])["results"]}
    assert scores == {"guardrail_correct": 1.0, "intent_correct": 1.0, "retrieval_hit": 1.0, "reciprocal_rank": 1.0, "keyword_recall": 0.5}
