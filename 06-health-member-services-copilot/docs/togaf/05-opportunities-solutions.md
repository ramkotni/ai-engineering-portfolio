# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Graph, tools with authz, guardrails, eval harness, deploy scripts | **Reuse** prototype | 74 tests, red-team suite, AgentCore deploy path exist |
| Contact-center vendor's AI agent (Amazon Connect/other) | **Evaluate in parallel** | May include handoff, telephony and voice, but weaker control over claim authorization and eval gates; revisit for voice channel |
| Generic chatbot platforms | Rejected | Claim-tool authorization and PHI controls are bespoke |
| LLM / embeddings / guardrails | **Buy** Bedrock | BAA, regional control |
| Knowledge Base | **Buy** Bedrock KB or OpenSearch | Managed |
| Identity | **Reuse** CIAM | - |
| Claims integration, handoff connector | **Build** | Vendor-specific |
| Red-team tooling | **Buy/reuse** (garak-style + own 31 cases) | Coverage |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Foundation | IaC, accounts, CI/CD, BAA verification, network | MVP |
| WP2 Identity and authorization | CIAM JWT, member-scoped claims tool, no-enumeration tests | MVP |
| WP3 Claims API connector (read-only) + mock | MVP |
| WP4 Knowledge base with plan/year metadata | MVP |
| WP5 Guardrails and PHI controls | Bedrock Guardrails, redaction coverage, tracing decision, retention | MVP |
| WP6 Durable memory + handoff | DynamoDB checkpointer, contact-center webhook | MVP |
| WP7 Compliance wording and disclosure | Denial templates, appeal-rights text | MVP |
| WP8 Eval gate and red-team in CI incl. known gaps | Phase 2 start |
| WP9 Representative assist, Spanish, voice | Phase 2 |
| WP10 Appeal-draft assistance (human submits), proactive notices | Target |

| Stage | Architecture | Exit |
|---|---|---|
| Baseline | Local Ollama/Chroma, 3 members | - |
| MVP (month 6) | AWS, CIAM, claims read-only, KB, guardrails, handoff, internal beta (employees as members) | Privacy/Security/Compliance sign-off |
| Phase 1 GA (month 9) | 10% -> 100% members, benefit + claim status + denial | KPIs, SLOs |
| Phase 2 (month 12-15) | Representative assist, Spanish, eval gate maturity | Containment target |
| Target | Voice, proactive guidance, appeal drafting | - |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| Claims platform API and rate limits | Not available; PHI approvals slow | Mock first; early data-access request |
| Compliance review cycle | Wording changes delay | Templates approved early; wording config-driven |
| Bedrock quotas | Throttling at peak | Quota request in month 1; retries; queue |
| CIAM claims (plan, member id) | Missing attributes | Eligibility lookup fallback |
| Contact-center integration | Vendor constraints | Webhook + email fallback |
| LangSmith PHI policy | Privacy veto | Hide inputs/outputs or self-host from day 1 |

## Open questions
Is the first release member-facing or representative-facing (lower risk)? A staged option: representative-assist first, member-facing after 3 months of quality data.
