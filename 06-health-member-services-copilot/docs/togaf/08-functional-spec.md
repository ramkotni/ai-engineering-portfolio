# 08 - Functional Specification

## Modules
| Module | Inputs | Processing | Outputs | Validations / errors |
|---|---|---|---|---|
| API edge | `ChatRequest` {question 1-8000 chars, session_id?, member_id? (ignored in prod)} | JWT/`x-api-key` check, PII redaction, session id issue | validated request | 401 invalid auth; 422 invalid body; 429 rate limit |
| `input_guard` | redacted text | Injection patterns (incl. possessive/"forget everything" variants), length, out-of-scope checks; Bedrock `ApplyGuardrail` (PROMPT_ATTACK, denied topics) | pass or `blocked` | Blocked -> `output_guard` with refusal, no LLM call |
| `supervisor` | text, memory | Classify intent: policy_question, claim_status, claim_denial (claims + policy), out_of_scope, handoff; rewrite follow-ups to standalone | route | Invalid classification -> policy route with low confidence |
| `retrieve` | query, member plan/year | KB search k=4 with plan filter | chunks + scores | Empty -> grader fails |
| `grade` | chunks | Relevance threshold (0.35 Titan / 0.50 nomic) ; at most one rewrite | relevant chunks or rewrite | Still none -> fallback to escalation |
| `claims_agent` | claim id(s), member id from token | `ClaimsRepository.get_claim/list_claims` scoped to member; identical reply for not found / not yours | claim facts | Authz fail -> `authz_denied` flag, generic reply |
| `generate` | question, claim facts, excerpts, history | Prompt by intent: cite sources, quote claim fields, include next steps; no medical advice | draft | Timeout -> retry once -> static fallback |
| `critic` | draft, evidence | Groundedness: numeric check + Claude fact-check (`GROUNDEDNESS_MODE=both`) | grounded true/false | Fail -> regenerate once, then escalate |
| `direct_response` | intent | Greetings, thanks, handoff offers, out-of-scope refusals | short reply | - |
| `output_guard` | answer | PII redaction, Bedrock guardrail on output, disclosure/appeal-rights text added by code for denials | final answer | Violation -> safe message |
| `finalize` | state | Persist redacted turn in checkpointer (TTL), emit audit and trace | response with `answer`, `intent`, `citations`, `grounded`, `guardrail`, `trace`, `latency_ms`, `run_id` | - |
| Feedback | run_id, score, comment | Store + attach to trace | 202 | Unknown run id -> 404 |

## Roles and permissions
| Actor | Policy Q&A | Own claims | Other members' claims | Admin endpoints |
|---|---|---|---|---|
| Member (JWT) | Y | Y | N (identical not-found) | N |
| Representative (SSO, member context) | Y | Only the selected member (Phase 2) | N | N |
| System caller (`x-api-key`) | Y | Only with a delegated member token | N | N |
| Admin / ops | metrics, health | N | N | Y |

## UI behavior
Chat widget with "AI assistant" label and a persistent "Talk to a person" button; typing indicator and streaming; answer cards with citation chips (document name, section) and for claims a compact claim summary card; quick replies for common questions; thumbs up/down; clear "New conversation" control; error banner with phone number on failure; plain language (grade 8); accessible (ARIA live region for new messages, keyboard navigation). The demo UI also shows the agent trace and guardrail flags (disabled for members in production).

## AI behavior specification
| Aspect | Spec |
|---|---|
| Tone | Warm, plain language, concise; avoid insurance jargon; empathetic for denials ("I understand this is frustrating") without promising outcomes |
| Citations | Every policy statement cites document and section; claim facts attributed to "your claim record" |
| Required text | Denial explanations end with the approved appeal rights and deadline text from the template store (added by code) |
| Refusals | Medical advice, other members' data, system prompt, off-topic: brief refusal plus an alternative (clinician, handoff, benefits info) |
| Confidence | Retrieval below threshold, ungrounded after one regeneration, or intent unclear twice -> escalate instead of answering |
| Numbers | Amounts, dates, codes only from context or claim record |
| Fallback-to-human | Not documented; disputes; appeals; distress/emergency language (emergency guidance first); repeated dissatisfaction; explicit request |
| Memory | Redacted conversation summary; no PHI beyond what the session needs; expires |

## Open questions
Exact denial templates per denial code (PA-01, OON-05, TF-02, others); state-specific language; distress-detection method.
