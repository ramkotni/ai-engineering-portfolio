# 08 - Functional Specification

## Modules
| Module | Inputs | Processing | Outputs | Validations / errors |
|---|---|---|---|---|
| `analyze_query` | question, role | Length <= 1,000 chars; injection regex; unsafe-request patterns (how to defeat protections; reports of past violations allowed); PII redaction (emails/phones -> `[email]`, `[phone]`; plant extensions kept); emergency detection (fire, injury, spill...) | clean text, flags | Blocked -> `guardrail_block` with fixed message; too long -> "ask one specific question" |
| `route_question` | text, role sources | LLM typed output `{primary_source, secondary_sources, confidence, rationale}`; keyword router on LLM failure; `plan_retrieval()` policy: confidence < 0.6 -> all allowed sources; confident out-of-scope -> decline; emergency -> safety mandatory; hands-on maintenance -> safety mandatory | retrieval plan | Role-disallowed sources removed |
| `retrieve` (x N, parallel) | text, source | Hybrid vector + BM25 with RRF (k=60), TOP_K 5 | chunks per source | Empty -> no chunks |
| `grade_documents` | chunks | De-duplicate; keep cosine >= 0.55; keep best chunk of mandatory sources; interleave sources; max 6 | graded chunks | None relevant -> rewrite once then `no_answer` |
| `rewrite_query` | text | LLM rewrite in plant terminology (once) | text | Re-routes |
| `generate` | excerpts | Prompt: answer only from numbered excerpts, cite `[n]`, copy numbers, otherwise "the documentation does not cover this"; per-source answer rules | draft | LLM failure -> verbatim top excerpts |
| `check_grounding` | draft | Citation validity (remove bad `[n]`, flag no citations); numeric grounding; unsafe-advice filter; optional LLM verifier (lists unsupported claims) | pass/fail + issues | Fail -> regenerate once with issues |
| `finalize` | draft, flags | Emergency banner prepended; caveat if still unverified; withhold unsafe answers | final answer | - |
| `no_answer` / `out_of_scope` / `guardrail_block` | state | Escalation contact / polite decline / fixed block message | terminal outputs | - |
| Role filter | role | `roles.yaml` sources; safety always allowed | allowed sources | Unknown role -> 401 |
| Observability | request | metrics, audit, LangSmith (feedback as supervisor rating) | - | Never fails request |

## Roles and permissions
| Role | Safety | Maintenance | Quality |
|---|---|---|---|
| floor_supervisor | Y | Y | Y |
| maintenance_technician | Y | Y | N |
| quality_engineer | Y | N | Y |
| ehs_manager | Y | Y | Y |
| contractor | Y | N | N |
Outcome codes: `answered`, `no_answer`, `out_of_scope`, `blocked`.

## UI behavior
Large-type single input with example chips; progress state with step labels (Routing, Searching safety, Writing); emergency banner pinned in red above everything; answer in numbered steps; citation chips (doc title, revision, section) opening the excerpt (and a deep link to the controlled document); "Not covered" card with owner contact and one-tap call/message; thumbs-up/down (safety answers ask for a reason); role badge; works in portrait and landscape; high-contrast mode.

## AI behavior specification
| Aspect | Spec |
|---|---|
| Tone | Plain, imperative, short sentences; steps numbered; no marketing language |
| Citations | `[n]` after every factual sentence, resolved to document ID, revision, section path |
| Refusals | Defeating protections: fixed message citing the relevant safety rule. Out-of-scope: "I can help with plant safety, maintenance and quality questions." |
| Confidence | Router < 0.6 -> search all allowed sources; cosine < 0.55 -> not used; nothing relevant after rewrite -> escalate; numeric mismatch after regeneration -> visible caveat "verify against the document" |
| Safety content | Hands-on work: LOTO and PPE first. Emergencies: banner first, then procedure. Never paraphrase numbers |
| Fallback-to-human | Not covered, caveated answer, or emergency -> escalation contact/emergency number displayed; permit-to-work remains the human control |
| Language | English (A-05) |

## Open questions
Wording of refusal and banner approved by EHS; whether safety answers should be verbatim quotes only.
