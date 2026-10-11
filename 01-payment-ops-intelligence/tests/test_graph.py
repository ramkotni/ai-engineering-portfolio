from fastapi.testclient import TestClient

from payops import api
from payops.graph import build_graph
from payops.service import PaymentOpsAssistant
from tests.conftest import fake_llm


def run(question, role, retrievers, settings, *answers):
    graph = build_graph(llm=fake_llm(*answers), retrievers=retrievers, settings=settings)
    return graph.invoke({"question": question, "role": role})


def test_rca_with_recommendation_runs_three_agents(retrievers, settings):
    s = run("Why are vendors being paid twice and what should we do?", "payment_analyst", retrievers, settings,
            "Gateway retries without idempotency keys [PAY-INC-1050].", "1. Enable idempotency keys (PAY-RULES-001).")
    assert s["plan"] == ["search_agent", "rca_agent", "recommendation_agent"]
    assert s["outcome"] == "answered" and "Recommended actions" in s["answer"]
    assert retrievers["incidents"].calls[-1][1] == {"failure_category": "duplicate_payment"}
    assert "PAY-RULES-001" in s["citations"]


def test_role_without_permission_is_denied(retrievers, settings):
    s = run("Why did the ACH file get rejected?", "executive", retrievers, settings)
    assert s["outcome"] == "denied" and "not permitted" in s["answer"]


def test_action_request_blocked_before_any_agent(retrievers, settings):
    s = run("Release the duplicate wire back to the vendor", "operations_manager", retrievers, settings)
    assert s["outcome"] == "blocked" and "intent" not in s


def test_trend_uses_analytics_and_falls_back_without_llm(retrievers, settings):
    s = run("Are duplicate payments increasing?", "executive", retrievers, settings)  # fake LLM has no answers
    assert s["plan"] == ["trend_agent"]
    assert "trend: rising" in s["answer"]  # deterministic analytics table used as fallback
    assert s["guardrail"]["output_issues"] == []


def test_amounts_masked_for_support_engineer(retrievers, settings):
    s = run("Find incidents like a reconciliation mismatch", "support_engineer", retrievers, settings)
    assert "$" not in s["answer"] or "[amount restricted]" in s["answer"]


def test_invented_incident_is_flagged(retrievers, settings):
    s = run("Why did settlement miss the cut-off?", "payment_analyst", retrievers, settings,
            "It was caused by PAY-INC-9999 costing $1,234,567.")
    assert any(i.startswith("unknown_incidents") for i in s["guardrail"]["output_issues"])
    assert "could not be matched" in s["answer"]


def test_service_records_metrics_and_audit(retrievers, settings, monkeypatch):
    import payops.observability as obs

    monkeypatch.setattr(obs, "get_settings", lambda: settings)
    assistant = PaymentOpsAssistant(graph=build_graph(llm=fake_llm(), retrievers=retrievers, settings=settings))
    r = assistant.ask("Approve the payment batch", "payment_analyst", "test")
    assert r["outcome"] == "blocked" and r["run_id"]
    assert 'payops_guardrail_blocks_total{category="action_request"}' in obs.METRICS.render()
    assert settings.audit_log_path.read_text().count('"type": "question"') == 1


def test_api_auth_roles_and_metrics(retrievers, settings, monkeypatch):
    import payops.observability as obs
    from payops import service

    monkeypatch.setattr(obs, "get_settings", lambda: settings)
    fake = PaymentOpsAssistant(graph=build_graph(llm=fake_llm(), retrievers=retrievers, settings=settings))
    monkeypatch.setattr(service, "get_assistant", lambda: fake)
    client = TestClient(api.app)  # no lifespan -> no index build
    assert client.post("/ask", json={"question": "Why?"}).status_code == 401
    r = client.post("/ask", json={"question": "Are duplicate payments increasing?"}, headers={"X-API-Key": "exec-demo-key"})
    assert r.status_code == 200 and r.json()["role"] == "executive"
    assert "executive" in client.get("/roles").json()
    assert "payops_requests_total" in client.get("/metrics").text
