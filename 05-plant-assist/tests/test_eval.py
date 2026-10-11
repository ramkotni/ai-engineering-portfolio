from eval.langsmith_eval import (
    expected_doc_cited,
    fact_recall,
    numbers_grounded,
    route_correct,
)
from eval.run_eval import evaluate_guardrails
from eval.run_eval import fact_recall as local_fact_recall


def test_guardrail_eval_set_is_fully_separated():
    result = evaluate_guardrails()
    assert result["block_precision"] == 1.0 and result["block_recall"] == 1.0, result["misclassified"]


def test_fact_recall_normalises_case_and_thousands_separators():
    assert local_fact_recall("Replace every 1000 operating hours", ["1,000"]) == 1.0
    assert local_fact_recall("Check the EHS manager", ["EHS Manager", "ext. 4400"]) == 0.5
    assert local_fact_recall("anything", []) is None


def test_langsmith_evaluators():
    ref = {"expected_source": "maintenance", "expected_docs": ["MM-HP-200"], "expected_facts": ["210"]}
    out = {"primary_source": "maintenance", "cited_docs": ["MM-HP-200"], "answer": "Torque to 210 ft-lb",
           "guardrail": {"output_issues": []}}
    assert route_correct(out, ref)["score"] == 1
    assert expected_doc_cited(out, ref)["score"] == 1
    assert fact_recall(out, ref)["score"] == 1.0
    assert numbers_grounded(out)["score"] == 1
    assert numbers_grounded({"guardrail": {"output_issues": ["unsupported_numbers:250"]}})["score"] == 0
