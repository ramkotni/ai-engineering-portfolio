# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Evidence in the prototype |
|---|---|---|
| Business | **Safety first.** Hands-on maintenance always brings lockout/tagout and PPE; emergencies get a fixed banner before anything else | Safety-first routing policy; emergency banner prepended by code |
| Business | **Never guess.** If documentation does not cover a question, escalate to the document owner | Relevance gate -> rewrite once -> `no_answer` with escalation contact |
| Business | Controlled documents stay authoritative; every fact cites document, revision and section | `[n]` citations |
| Business | The assistant never helps defeat a protection (interlocks, guards, e-stops, LOTO, PPE) | Unsafe-request guardrail |
| Data | One index per source (safety, maintenance, quality) so ownership, refresh and access stay separable | One Chroma collection per source |
| Data | Structure is preserved: per section, tables whole, contextual headers | Structure-aware chunking |
| Application | One agentic workflow, not multi-agent; bounded loops | ADR in DESIGN; 1 rewrite, bounded generation attempts |
| Application | Deterministic guardrails first, LLM verifier second | Rules run on every request, even with the verifier off |
| Technology | Provider-neutral: Ollama locally, Bedrock by configuration | Env-var switch |
| Responsible AI | Numeric grounding: every number must appear in excerpts or the question | Torques, pressures and limits are exact |
| Responsible AI | Safety is searchable by every role, including contractors | `safety` always allowed |

## Governance and RACI
| Activity | Plant Manager (PO) | Enterprise Architect | AI Lead | EHS Manager | Quality Manager | Maintenance Manager | Security |
|---|---|---|---|---|---|---|---|
| Scope and priorities | A | C | C | C | C | C | I |
| Architecture / ADRs | C | A | R | C | I | I | C |
| Safety rules (unsafe-request patterns, emergency banner, mandatory LOTO) | I | C | R | **A** | I | C | I |
| Source content and revisions | I | I | I | R (safety) | R (quality) | R (maintenance) | I |
| Role-to-source mapping | C | I | I | C | C | C | A |
| Prompt/model change | C | I | A/R | C | C | C | C |
| Go-live | A | C | R | R | C | C | R |

**ARB:** fortnightly in build, monthly after GA. EHS holds a veto on safety behaviour. Document owners are accountable for the content the assistant cites.

## Tailored ADM
Light Preliminary/A. B maps the three document-owner processes and the escalation path. C separates ingestion/document lifecycle from the question-answering workflow. D chooses AWS container hosting suited to tablets on the floor. E/F: MVP (one plant, three sources) -> Phase 2 (multi-turn, MES/CMMS context, multi-plant) -> Target. G/H integrate with document control and EHS change control.

## Assumptions and open questions
- A-01 ~250 users, 3 shifts; A-02 not classified as high-risk AI under the EU AI Act, but it is advisory content for safety-relevant work and is governed as such.
- Q: Will EHS accept AI-generated answers on safety procedures, or must safety answers be quoted verbatim (extractive mode)?
- Q: Which languages do plant staff need (A: English first)?
