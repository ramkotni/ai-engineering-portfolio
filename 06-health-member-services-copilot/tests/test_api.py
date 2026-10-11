from fastapi.testclient import TestClient

from app.api import app


def _client(service):
    app.state.service = service
    return TestClient(app)


def test_health_and_ping(service):
    with _client(service) as c:
        assert c.get("/ping").json() == {"status": "Healthy"}
        assert c.get("/health").json()["status"] == "ok"


def test_chat_endpoint(service):
    with _client(service) as c:
        r = c.post("/chat", json={"question": "What is the deductible?", "member_id": "M1001"})
        assert r.status_code == 200
        body = r.json()
        assert body["answer"] and body["session_id"] and body["intent"] == "policy_question"


def test_agentcore_invocations_uses_session_header(service):
    with _client(service) as c:
        r = c.post(
            "/invocations",
            json={"prompt": "What is the deductible?", "member_id": "M1001"},
            headers={"X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": "agentcore-session-0000000000000000001"},
        )
        assert r.status_code == 200
        assert r.json()["session_id"] == "agentcore-session-0000000000000000001"


def test_chat_validation_error(service):
    with _client(service) as c:
        assert c.post("/chat", json={"question": ""}).status_code == 422
