"""End-to-end test against the real stack (Ollama or Bedrock + Chroma index).

Opt in with:  RUN_INTEGRATION=1 pytest tests/test_integration.py -s
"""

import os

import pytest

pytestmark = pytest.mark.skipif(os.getenv("RUN_INTEGRATION") != "1", reason="set RUN_INTEGRATION=1")


@pytest.fixture(scope="module")
def assistant():
    from plant_assist.ingest import ensure_index
    from plant_assist.service import PlantAssistant

    ensure_index()
    return PlantAssistant()


@pytest.mark.parametrize(
    "question, expected_source, expected_doc",
    [
        ("How often should the return-line filter be replaced on the HP-200?", "maintenance", "MM-HP-200"),
        ("What are the Western Electric out-of-control rules?", "quality", "QCS-002"),
        ("What PPE is required at the sodium hydroxide parts washer?", "safety", "SOP-SAF-003"),
    ],
)
def test_routes_and_cites(assistant, question, expected_source, expected_doc):
    result = assistant.ask(question)
    assert result["route"]["primary_source"] == expected_source
    assert expected_doc in {c["doc_id"] for c in result["citations"]}
    assert result["outcome"] == "answered"
