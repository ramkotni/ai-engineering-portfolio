"""Graph tests with a fake chat model and in-memory retrievers - no Ollama, AWS or index needed.

GenericFakeChatModel does not support structured output, so these tests also exercise the
fallback paths: keyword routing and 'grounding check unavailable'.
"""

from langchain_core.language_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from plant_assist import nodes as nodes_module
from plant_assist.config import Settings
from plant_assist.graph import build_graph
from plant_assist.ingest import load_source_documents, parse_front_matter
from plant_assist.nodes import EMERGENCY_BANNER
from plant_assist.router import RouteDecision
from plant_assist.sources import SOURCES


def chunk(source, doc_id, section, content, score):
    return {
        "source": source, "doc_id": doc_id, "title": doc_id, "section": section, "revision": "A",
        "content": f"{doc_id} - {section}\n{content}", "score": score, "bm25": 1.0, "rrf": score / 10,
    }


class FakeRetriever:
    def __init__(self, hits):
        self.hits = hits
        self.queries: list[str] = []

    def search(self, query, k):
        self.queries.append(query)
        return [dict(h) for h in self.hits[:k]]


def make_graph(answers, retrievers, **settings):
    llm = GenericFakeChatModel(messages=iter([AIMessage(content=a) for a in answers]))
    return build_graph(llm=llm, retrievers=retrievers, settings=Settings(_env_file=None, **settings))  # ignore local .env


def default_retrievers(score=0.8):
    return {
        "safety": FakeRetriever([chunk("safety", "SOP-SAF-001", "Energy Isolation Steps", "Apply LOTO.", score)]),
        "maintenance": FakeRetriever([chunk("maintenance", "MM-HP-200", "Replacing the Main Cylinder Seal Kit", "Torque to 210 ft-lb.", score)]),
        "quality": FakeRetriever([chunk("quality", "QCS-002", "Control Charts", "Subgroup of 5.", score)]),
    }


def test_repair_question_routes_to_maintenance_and_pulls_safety():
    retrievers = default_retrievers()
    graph = make_graph(["Apply LOTO [2]. Torque bolts to 210 ft-lb [1]."], retrievers)

    result = graph.invoke({"question": "How do I replace the seal on the HP-200 hydraulic press?"})

    assert result["outcome"] == "answered"
    assert result["route"]["method"] == "keyword-fallback"
    assert [t["source"] for t in result["targets"]] == ["maintenance", "safety"]
    assert {c["doc_id"] for c in result["citations"]} == {"MM-HP-200", "SOP-SAF-001"}
    assert retrievers["safety"].queries[0].startswith("Lockout/tagout")
    assert retrievers["quality"].queries == []          # not searched
    assert result["grounded"] is None                    # checker unavailable with fake model


def test_emergency_gets_deterministic_banner():
    graph = make_graph(["Evacuate the area and apply LOTO [1]."], default_retrievers())
    result = graph.invoke({"question": "Chemical spill and someone is injured near line 3"})
    assert result["safety_alert"] is True
    assert result["answer"].startswith(EMERGENCY_BANNER)


def test_no_relevant_docs_rewrites_once_then_escalates():
    retrievers = default_retrievers(score=0.2)  # below min_relevance everywhere
    graph = make_graph(["rewritten question about press oil"], retrievers, max_query_rewrites=1)

    result = graph.invoke({"question": "What oil goes in the press?"})

    assert result["outcome"] == "no_answer"
    assert result["rewrite_count"] == 1
    assert "ext. 4410" in result["answer"]               # maintenance escalation contact
    assert any(line.startswith("rewrite_query") for line in result["trace"])


def test_confident_out_of_scope_short_circuits(monkeypatch):
    monkeypatch.setattr(
        nodes_module, "llm_route",
        lambda llm, q: RouteDecision(primary_source="out_of_scope", confidence=0.95, rationale="lunch"),
    )
    retrievers = default_retrievers()
    result = make_graph([], retrievers).invoke({"question": "What's for lunch today?"})
    assert result["outcome"] == "out_of_scope"
    assert all(r.queries == [] for r in retrievers.values())


def test_ungrounded_answer_is_regenerated_then_flagged(monkeypatch):
    calls = []

    class Verdict:
        grounded = False
        unsupported_claims = ("made-up torque",)

    class FakeChecker:
        def invoke(self, messages):
            calls.append(messages)
            return Verdict()

    monkeypatch.setattr(nodes_module, "structured", lambda llm, schema: FakeChecker())
    monkeypatch.setattr(
        nodes_module, "llm_route",
        lambda llm, q: RouteDecision(primary_source="quality", confidence=0.9, rationale="spc"),
    )
    graph = make_graph(["first [1]", "second [1]"], default_retrievers(), max_generation_attempts=2)
    result = graph.invoke({"question": "What subgroup size for X-bar charts?"})

    assert result["generation_attempts"] == 2 and len(calls) == 2
    assert "could not be verified" in result["answer"]


def test_ingestion_parses_front_matter_and_sections():
    meta, body = parse_front_matter("---\ndoc_id: X-1\ntitle: T\n---\n# T\n## S\ntext")
    assert meta["doc_id"] == "X-1" and body.startswith("# T")

    for source in SOURCES.values():
        docs = load_source_documents(source)
        assert docs, f"no synthetic docs for {source.name}"
        assert all(d.metadata["source"] == source.name and d.metadata["doc_id"] for d in docs)
