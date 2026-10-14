# 00 - Preliminary Phase

## Architecture principles
| Area | Principle | Evidence in the prototype |
|---|---|---|
| Business | **Information and explanation, not adjudication.** The copilot never decides, changes or reprocesses a claim, and gives no medical advice | Claims tool is read-only; scope limited to benefits and claim explanations |
| Business | Cited, consistent answers; escalate to a human instead of guessing | Citations; "not in the documents" escalation (acupuncture example) |
| Business | A member never sees another member's data | `ClaimsRepository.get_claim` identical reply for "not found" and "not yours" |
| Data | **Minimum necessary PHI** reaches any model; PII redacted before the graph runs | Redaction in the edge node; hashed member id in traces |
| Data | Authorization is enforced in code, not in the prompt | Tool-level authz |
| Application | Supervisor routes to specialist agents; bounded loops (rewrite, regenerate) | LangGraph graph with critic |
| Application | One `KnowledgeBase` interface; local and AWS parity from one codebase | Chroma or Bedrock Knowledge Bases |
| Technology | Identity comes from a verified token, never the request body | README: production requires JWT |
| Technology | Defence in depth: local rules + Bedrock Guardrails (ML classifiers) | Known gaps need ML filters |
| Responsible AI | Quality gates block deploys; red-team suite is part of CI | `eval.run_eval` exits non-zero on gate failure; 31-case red-team |
| Responsible AI | Fairness and accessibility: plain language, consistent answers across plans and member groups | Fairness evaluation (file 09) |
| Responsible AI | Disclosure: members know they are talking to an AI and can reach a human | UI requirement |

## Governance and RACI
| Activity | Head of Member Services (PO) | Enterprise Architect | AI Lead | Privacy Officer | Security | Compliance/Legal | Claims Ops |
|---|---|---|---|---|---|---|---|
| Scope and priorities | A | C | C | C | I | C | C |
| Architecture / ADRs | C | A | R | C | C | I | I |
| PHI handling, BAA, retention | I | C | C | A | R | C | I |
| Member-facing wording (denial explanations, disclaimers) | C | I | R | C | I | A | C |
| Claims API access | C | C | I | C | A | I | R |
| Prompt/model change | C | I | A/R | C | C | C | C |
| Go-live | A | C | R | R | R | R | C |

**ARB:** fortnightly during build, monthly after GA; extra review for any change touching PHI flow, authorization, guardrails or member-facing wording. Compliance holds a veto on denial-explanation wording.

## Tailored ADM
Preliminary/A light but with a compliance workstream. B centres on contact-center and member journeys with handoff. C separates PHI-bearing data flows from policy content. D uses AWS HIPAA-eligible services only (verify per service, A-04). E/F: MVP (policy Q&A + claim status, member portal) -> Phase 2 (representative assist, more intents) -> Target (proactive guidance). G/H connect to HIPAA risk management and change control.

## Assumptions and open questions
- A-01 ~150,000 members; A-02 US-only operations; A-03 EU AI Act not in scope; A-04 AWS BAA in place and each used service is on the HIPAA-eligible list (to be verified by Privacy/Security).
- Q: May the model provider process claim detail under the BAA (with zero retention), or must claim fields be tokenized before the LLM?
- Q: Which member-communication rules apply to denial explanations (required language, appeal rights wording)?
