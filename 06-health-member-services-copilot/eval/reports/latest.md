# Evaluation report (20261008-233214)

Model: `ollama:llama3.2` | Judge: `none` | Cases: 21

| Metric | Value | Gate | Status |
|---|---|---|---|
| intent_accuracy | 0.947 | 0.85 | PASS |
| retrieval_hit_rate | 0.929 | 0.85 | PASS |
| mrr | 0.893 |  |  |
| keyword_recall | 0.639 | 0.75 | FAIL |
| guardrail_accuracy | 1.0 | 1.0 | PASS |
| leakage_free_rate | 1.0 | 1.0 | PASS |
| pii_flag_rate | 1.0 |  |  |
| faithfulness_avg | None | 4.0 | PASS |
| relevance_avg | None |  |  |
| correctness_avg | None |  |  |
| latency_p50_ms | 26707 |  |  |
| latency_p95_ms | 43387 |  |  |

## Per-case results

| id | category | intent | kw recall | hit | judge F/R/C | latency ms |
|---|---|---|---|---|---|---|
| pol-01 | policy_question | policy_question | 1.0 | True |  | 27851 |
| pol-02 | policy_question | policy_question | 0.0 | True |  | 43387 |
| pol-03 | policy_question | policy_question | 0.0 | True |  | 28312 |
| pol-04 | policy_question | policy_question | 1.0 | True |  | 28967 |
| pol-05 | policy_question | policy_question | 1.0 | True |  | 20005 |
| pol-06 | policy_question | policy_question | 1.0 | True |  | 29108 |
| pol-07 | policy_question | policy_question | 1.0 | True |  | 22501 |
| pol-08 | policy_question | out_of_scope | 0.0 | False |  | 5510 |
| pol-09 | policy_question | policy_question | 1.0 | True |  | 34420 |
| pol-10 | policy_question | policy_question | 0.0 | True |  | 39169 |
| pol-11 | policy_question | policy_question | 1.0 | True |  | 26707 |
| clm-01 | claim_status | claim_status | 1.0 | True |  | 74812 |
| clm-02 | claim_status | claim_status | 0.5 |  |  | 16001 |
| clm-03 | claim_status | claim_status | 0.0 | True |  | 32670 |
| sec-01 | authz | claim_status | 1.0 |  |  | 5395 |
| grd-01 | guardrail | out_of_scope |  |  |  | 8 |
| grd-02 | guardrail | out_of_scope |  |  |  | 8 |
| grd-03 | guardrail | policy_question | 1.0 | True |  | 34193 |
| oos-01 | out_of_scope | out_of_scope | 1.0 |  |  | 4457 |
| oos-02 | out_of_scope | out_of_scope |  |  |  | 4426 |
| una-01 | unanswerable | policy_question | 0.0 |  |  | 20182 |