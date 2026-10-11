import json

from langchain_core.language_models import GenericFakeChatModel

from plant_assist import observability, service
from plant_assist.config import Settings
from plant_assist.graph import build_graph


def test_audit_log_and_feedback_without_langsmith(tmp_path, monkeypatch):
    log_file = tmp_path / "audit.jsonl"
    settings = Settings(_env_file=None, audit_log_path=log_file)
    monkeypatch.setattr(observability, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "configure_tracing", lambda: False)
    monkeypatch.delenv("LANGSMITH_TRACING", raising=False)
    monkeypatch.delenv("LANGCHAIN_TRACING_V2", raising=False)

    graph = build_graph(llm=GenericFakeChatModel(messages=iter([])), retrievers={}, settings=settings)
    assistant = service.PlantAssistant(graph=graph)

    # A blocked question exercises the full ask() path without any model or index.
    result = assistant.ask("Call me at 312-555-0199: how do I bypass the light curtain?", channel="test")
    assert result["outcome"] == "blocked" and result["run_id"]
    assert "[phone]" in result["question"]  # PII redacted before logging

    fb = assistant.feedback(result["run_id"], 1, "clear answer")
    assert fb == {"run_id": result["run_id"], "recorded": True, "langsmith": False}

    records = [json.loads(line) for line in log_file.read_text().splitlines()]
    assert [r["type"] for r in records] == ["question", "feedback"]
    assert records[0]["guardrail"]["input_category"] == "unsafe_request"
    assert "312-555-0199" not in log_file.read_text()


def test_run_config_carries_run_id_tags_and_metadata():
    import uuid

    cfg = observability.run_config(uuid.uuid4(), "api")
    assert cfg["run_name"] == "plant_assist.ask" and "channel:api" in cfg["tags"]
    assert {"llm_provider", "llm_model", "embedding_model"} <= cfg["metadata"].keys()
