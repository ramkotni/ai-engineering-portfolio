from plant_assist.retrieval import BM25, tokenize
from plant_assist.router import (
    SAFETY_QUERY_PREFIX,
    RouteDecision,
    keyword_route,
    plan_retrieval,
)


def _sources(targets):
    return [t.source for t in targets]


def test_keyword_route_picks_domain():
    assert keyword_route("When do I change the return-line filter on the HP-200 press?").primary_source == "maintenance"
    assert keyword_route("What PPE and gloves are needed for chemical handling?").primary_source == "safety"
    assert keyword_route("What AQL and sample size for incoming inspection?").primary_source == "quality"


def test_keyword_route_unknown_is_low_confidence_not_refusal():
    decision = keyword_route("tell me something interesting")
    assert decision.primary_source == "out_of_scope"
    assert decision.confidence < 0.6


def test_low_confidence_fans_out_to_all_sources():
    d = RouteDecision(primary_source="quality", confidence=0.4, rationale="unsure")
    assert set(_sources(plan_retrieval(d, "parts look wrong", False, 0.6))) == {"safety", "maintenance", "quality"}


def test_confident_out_of_scope_skips_retrieval():
    d = RouteDecision(primary_source="out_of_scope", confidence=0.95, rationale="cafeteria")
    assert plan_retrieval(d, "what's for lunch", False, 0.6) == []


def test_hands_on_maintenance_adds_safety_with_loto_query():
    d = RouteDecision(primary_source="maintenance", confidence=0.9, rationale="repair")
    targets = plan_retrieval(d, "How do I replace the seal kit on HP-200?", False, 0.6)
    assert _sources(targets) == ["maintenance", "safety"]
    safety = targets[1]
    assert safety.mandatory and safety.query.startswith(SAFETY_QUERY_PREFIX)


def test_informational_maintenance_question_does_not_add_safety():
    d = RouteDecision(primary_source="maintenance", confidence=0.9, rationale="spec")
    assert _sources(plan_retrieval(d, "What oil grade does the HP-200 use?", False, 0.6)) == ["maintenance"]


def test_emergency_forces_safety_even_if_router_says_out_of_scope():
    d = RouteDecision(primary_source="out_of_scope", confidence=0.9, rationale="?")
    targets = plan_retrieval(d, "there is smoke coming from panel 4", True, 0.6)
    assert _sources(targets) == ["safety"] and targets[0].mandatory


def test_bm25_prefers_exact_terms_and_stems():
    bm25 = BM25(["major spill response evacuate", "belt tension deflection", "gland retainer bolts 210 ft-lb"])
    scores = bm25.scores("someone spilled solvent")
    assert scores.index(max(scores)) == 0
    assert tokenize("Spilled replacing") == tokenize("spill replace")
