# 08 - Functional Specification

## Modules
| Module | Inputs | Processing | Outputs | Validations / errors |
|---|---|---|---|---|
| Input guard | question text | injection patterns, action-command detection, PII redaction | clean text or `blocked` | Empty or > 2,000 chars -> 422; blocked -> outcome `blocked` with reason category |
| Intent agent | clean text | LLM structured output (search/rca/recommendation/trend/summary + category, system, payment type, months, confidence); fallback keyword classifier | intent + slots | Slots kept only if the question mentions them; invalid JSON -> fallback and `payops_intent_fallback_total++` |
| Authorize | intent, role | role lookup in `roles.yaml`, plan pruning | plan or `denied` | Unknown role -> 401; intent not allowed -> denied with allowed intents |
| Search | text, filters | hybrid vector+BM25 RRF, k=6, category filter | incidents + chunks | No results -> "insufficient evidence" |
| RCA | incidents | LLM ranks causes citing IDs | ordered causes | LLM failure -> top-3 root causes extracted |
| Recommendation | resolutions, rules, RCA | LLM composes numbered actions | actions with citations | LLM failure -> list past resolutions |
| Trend | filters | pandas groupby month/category/system, month-end share, MTTR | table + narrative | Narrative must not add numbers; no data -> "no matching incidents" |
| Summary | trend + Sev1/2 + report commentary | style by role (executive / operational) | summary | LLM failure -> fact list |
| Output guard | draft answer | numeric grounding, incident-ID grounding, bank/PII redaction, amount masking | final answer + flags | Ungrounded number -> visible caveat; unknown ID -> removed/flagged |
| Observability | every request | metrics, audit line, LangSmith trace | `/metrics`, audit.jsonl | Logging failure never fails the request |

## Roles and permissions
| Role | search | rca | recommendation | trend | summary | Amounts |
|---|---|---|---|---|---|---|
| payment_analyst | Y | Y | Y | Y | Y | Y |
| operations_manager | Y | Y | Y | Y | Y | Y |
| executive | N | N | N | Y | Y (exec) | Y |
| auditor | Y | N | N | Y | Y | Y |
| support_engineer | Y | Y | N | N | N | masked |

## UI behavior
Role selector (dev) / SSO role (prod); question box; answer panel with citations list; evidence expander; thumbs up/down; Metrics tab (admin only). Spinner with elapsed time; timeout message after 60 s with option to retry. Denied/blocked shown as an information banner, not an error.

## AI behavior specification
| Aspect | Spec |
|---|---|
| Tone | Concise, operational, neutral; executive style: 5-8 lines, no jargon |
| Citations | Every causal claim followed by `[PAY-INC-xxx]` or `[PAY-RULES-001 section]` |
| Refusals | Payment actions, bank-detail changes, instructions to ignore rules: "This assistant is read-only..." plus the allowed alternative |
| Confidence | Intent confidence < 0.5 -> keyword fallback; retrieval top score below tuned threshold -> "insufficient evidence", no RCA invented |
| Numbers | Only from evidence/analytics/question; otherwise caveat |
| Fallback-to-human | Answer marked `fallback`, or Sev1 mentioned -> "Escalate to on-call per runbook" |
| Language | English (A-05) |

## Open questions
Exact refusal wording approved by compliance; retrieval score threshold to be tuned on real data.
