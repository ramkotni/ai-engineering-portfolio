# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Evidence in the prototype |
|---|---|---|
| Business | **Advisory only.** Never dispatch, reboot, reconfigure or push firmware | Action-command guardrail |
| Business | **Safety first.** Never help bypass e-stop, lidar, bumpers, safety fields or enter restricted zones | Safety-override guardrail; unsafe advice withheld |
| Business | Zone-scoped access for third parties | `zones` in `roles.yaml` |
| Data | Measurements are queried, not embedded | Telemetry via pandas/numpy |
| Data | An incident/maintenance action is the unit of evidence | One chunk per row |
| Application | Fixed plan per intent; LLM only for intent and the last narration (2 calls instead of 5) | Cost and predictability |
| Application | Deterministic analytics own every number | Battery slope, risk score, rebalancing |
| Technology | Provider-neutral model layer; local fallback | Ollama / Bedrock |
| Technology | Observable end to end | LangSmith, `/metrics`, audit log |
| Responsible AI | Every ID and number in an answer must exist in evidence | Output grounding |
| Responsible AI | Humans approve operational changes (shift lead accepts task moves) | Next-step design |

## Governance and RACI
| Activity | Fleet Manager (PO) | Enterprise Architect | AI Lead | Safety/EHS | Security | Site Leadership |
|---|---|---|---|---|---|---|
| Scope and priorities | A | C | C | C | I | C |
| Architecture / ADRs | C | A | R | C | C | I |
| Safety guardrail rules | C | C | R | A | C | I |
| Risk-score and policy thresholds (e.g. battery replace < 75%) | A | I | R | C | I | I |
| Prompt / model change | C | I | A/R | C | C | I |
| Contractor access | R | I | I | C | A | I |
| Go-live | A | C | R | R | R | I |

**ARB:** fortnightly in build, monthly after GA; extra session for any change to safety guardrails, policy thresholds, zone scoping or model provider. Safety/EHS holds a veto on safety-guardrail changes.

## Tailored ADM
Light Preliminary/A; B focuses on maintenance and shift-handover processes; C merges data + application; D is AWS container-based; E/F stage MVP -> Phase 2 (live telemetry, approvals) -> Target (learned risk weights); G/H add change control for policy thresholds, since they change what the system recommends.

## Assumptions and open questions
- A-01 ~60 users; A-02 safety-standard obligations apply to advice content, not to robot control.
- Q: Who owns the policy thresholds (replace < 75% or > 1,800 cycles; inspect at > 0.3%/day)?
- Q: Can contractors' queries be logged with their identities under their contract?
