from fastapi.testclient import TestClient
from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from plant_assist import api, rbac
from plant_assist.config import Settings
from plant_assist.graph import build_graph
from plant_assist.service import PlantAssistant
from tests.test_graph import default_retrievers


def graph(answers, **settings):
    llm = GenericFakeChatModel(messages=iter([AIMessage(content=a) for a in answers]))
    return build_graph(llm=llm, retrievers=default_retrievers(), settings=Settings(_env_file=None, **settings))


def test_roles_load_and_safety_always_allowed():
    contractor = rbac.get_role("contractor")
    assert contractor.can_search("safety") and not contractor.can_search("maintenance")
    assert rbac.role_for_api_key("quality-demo-key").name == "quality_engineer"


def test_contractor_gets_safety_only_with_note():
    s = graph(["Apply LOTO [1]."], grounding_check=False).invoke(
        {"question": "How do I replace the seal on the HP-200 hydraulic press?", "role": "contractor"})
    assert [t["source"] for t in s["targets"]] == ["safety"] and s["restricted_sources"] == ["maintenance"]
    assert s["outcome"] == "answered" and "not available for your role" in s["answer"]


def test_quality_engineer_denied_maintenance_only_question():
    s = graph([]).invoke({"question": "What oil grade does the HP-200 press use?", "role": "quality_engineer"})
    assert s["outcome"] == "denied" and "cannot search Maintenance Manuals" in s["answer"]


def test_api_requires_key_and_exposes_metrics(tmp_path, monkeypatch):
    import plant_assist.observability as obs
    from plant_assist import service

    settings = Settings(_env_file=None, audit_log_path=tmp_path / "a.jsonl", grounding_check=False)
    monkeypatch.setattr(obs, "get_settings", lambda: settings)
    fake = PlantAssistant(graph=graph(["Apply LOTO [1]."], grounding_check=False))
    monkeypatch.setattr(service, "get_assistant", lambda: fake)
    c = TestClient(api.app)
    assert c.post("/ask", json={"question": "How do I replace the seal?"}).status_code == 401
    r = c.post("/ask", json={"question": "How do I replace the seal on the HP-200 press?"}, headers={"X-API-Key": "contractor-demo-key"})
    assert r.status_code == 200 and r.json()["role"] == "contractor"
    assert "plant_assist_requests_total" in c.get("/metrics").text
    assert c.get("/roles").json()["contractor"]["sources"] == ["safety"]
