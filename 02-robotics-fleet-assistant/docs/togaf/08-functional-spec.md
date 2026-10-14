# 08 - Functional Specification

## Modules
| Module | Inputs | Processing | Outputs | Validations / errors |
|---|---|---|---|---|
| Input guard | question | injection, safety-override, restricted-zone, action-command detection, PII redaction | clean text or `blocked` | Empty/over 2,000 chars -> 422; blocked -> reason category and safety-procedure pointer |
| Intent agent | text | LLM structured output: intent, robot ID, zone, event type; keyword fallback; slot grounding | intent + slots | Slots kept only if mentioned; bad JSON -> fallback + counter |
| Authorize | intent, slots, role | intent permission; robot/zone must be in role zones | plan or `denied` | Denied lists allowed intents or zones |
| Fleet Search | text, filters | hybrid retrieval (robot, event type, caller zones) + guide sections, k=10 | events + guide chunks | None found -> state so |
| Diagnostics | robot record + events + guide | LLM picks probable cause among 6 categories with event IDs and first action | diagnosis | LLM failure -> top event root cause |
| Battery | telemetry | least-squares 30-day slope per robot vs policy | table + flags | No telemetry -> message with as-of date |
| Predictive Maintenance | battery + registry + incidents | risk score = low health + cycles + PM age + decline + recent incidents | ranked list + reasons | Ties broken by cycles |
| Task Optimization | status | greedy within zone per BR-2 | proposals | No candidates -> "balanced" |
| Fleet Status | registry | counts and utilisation per zone | table | - |
| Ops Summary | all outputs + last week's incidents | style by role (technical, operational, executive) | report | LLM failure -> facts list |
| Output guard | draft | ID + number grounding; unsafe-advice detector; PII | final | Ungrounded -> caveat; unsafe -> withheld |
| Observability | request | metrics, audit, trace | `/metrics`, audit.jsonl | Never fails request |

## Roles and permissions
| Role | Intents | Zones |
|---|---|---|
| technician | diagnostics, navigation, battery, predictive maintenance, status | all |
| shift_lead | status, task assignment, summary, diagnostics, navigation | all |
| fleet_manager | all seven | all |
| site_executive | summary, status | all |
| contractor_technician | diagnostics, battery, navigation | Z1-Inbound |

## UI behavior
Role/user banner (zones shown); question box with example chips; answer with citation list (event IDs link to the event card); tables for battery/risk/proposals; "as of" timestamp on telemetry answers; thumbs; Metrics tab for admins. Denied/blocked displayed as an info banner with the safe alternative.

## AI behavior spec
| Aspect | Spec |
|---|---|
| Tone | Technical and short for technicians; operational for leads; executive: <= 6 lines, KPIs first |
| Citations | Event/maintenance IDs `[EVT-...]`, guide sections `[GUIDE section]` |
| Refusals | Safety bypass, restricted zones, execution commands. Template: "I can't help with that. Follow <procedure>. I can explain the fault or suggest a safe next step." |
| Confidence | Intent confidence < 0.5 or invalid output -> keyword fallback; no matching events -> low-confidence statement, guide only |
| Numbers | Must come from analytics; narration may not add numbers |
| Fallback-to-human | Fallback outcome, safety refusal repeat, or top-3 critical risk -> "Escalate to senior technician / EHS" |

## Open questions
Exact refusal text approved by EHS; freshness limit per intent.
