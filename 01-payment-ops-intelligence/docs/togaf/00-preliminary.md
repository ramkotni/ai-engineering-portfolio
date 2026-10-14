# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Rationale / evidence in the prototype |
|---|---|---|
| Business | **Read-only decision support.** The assistant never moves money or edits bank details | Guardrail refuses release/approve/cancel/re-send commands |
| Business | Evidence over fluency: every claim cites an incident or rule ID | Incident-ID grounding |
| Business | Role-appropriate views (analyst, manager, exec, auditor, contractor) | `roles.yaml` RBAC |
| Data | An incident is the unit of evidence (one chunk per CSV row) | Keeps symptom, root cause, resolution together |
| Data | Numbers come from code, not the LLM | pandas Trend Agent; numeric grounding |
| Data | Bank/PII data is redacted on the way in and out; amounts masked for contractors | Guardrails, `can_view_amounts` |
| Application | Deterministic agent plan per intent; LLM used only where language is needed | Predictable cost, auditable order |
| Application | Every model call has a non-LLM fallback | Keyword intent, extractive RCA/recommendation |
| Technology | Model-provider neutral (Ollama locally, Bedrock in cloud) behind one `llm.py` | Avoids lock-in |
| Technology | Everything observable: traces, metrics, audit log | LangSmith, `/metrics`, `audit.jsonl` |
| Responsible AI | Quality is gated by evaluation, not opinion | Golden datasets + RAGAS in CI (see 10) |
| Responsible AI | Humans decide: AI output is advisory; thumbs feedback is captured | `/feedback` |

## Governance model and RACI
R = Responsible, A = Accountable, C = Consulted, I = Informed.
| Decision / activity | Product Owner | Enterprise Architect | AI Lead | Security / Compliance | Ops Manager | Internal Audit |
|---|---|---|---|---|---|---|
| Scope and priorities | A | C | C | C | R | I |
| Architecture and ADRs | C | A | R | C | I | I |
| Prompt / model changes | C | I | A/R | C | C | I |
| Guardrail policy | C | C | R | A | C | C |
| Access roles and data classes | C | C | I | A | R | C |
| Go-live | A | C | R | R | R | I |
| Evidence/audit log retention | I | C | C | A | I | R |

**Architecture Review Board (ARB):** fortnightly during build, monthly after GA; extra session for any change to
guardrails, data classes, model provider or role permissions. Quorum: Enterprise Architect, AI Lead, Security,
Product Owner. Output: recorded decision (ADR in `12`).

## Tailored ADM approach
| ADM phase | Tailoring for this project |
|---|---|
| Preliminary / A | Lightweight: one vision doc; the prototype is the baseline |
| B | Focus on the investigation process and HITL points; no org redesign |
| C | Data and application together (small system); AI architecture is first-class |
| D | Cloud-first on AWS; containers; managed vector store decision |
| E/F | MVP -> Phase 2 -> Target transition architectures; cost model dominated by people |
| G/H | Compliance reviews at each release; drift and prompt changes through change control |
| Requirements | Single catalog with REQ -> US -> TC traceability (file 12) |

## Assumptions and open questions
- A-01 ~40 users, A-02 SOX/PCI/GDPR relevant. Confirm real user counts and regulatory scope.
- Q: Which ITSM and monitoring tools feed incidents/reports in production?
- Q: Is the model allowed to see unmasked vendor names, or must they be tokenized?
