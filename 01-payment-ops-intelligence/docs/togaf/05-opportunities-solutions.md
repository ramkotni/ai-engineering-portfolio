# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Agent graph, guardrails, grounding, RBAC | **Reuse** prototype code | Already tested (29 tests) and domain-specific |
| LLM | **Buy** (Bedrock) | No GPU ops; in-region data handling |
| Vector/search | **Buy** (OpenSearch managed) | HA, hybrid search, snapshots |
| Identity | **Reuse** corporate IdP | Mandatory SSO |
| Observability | **Buy** LangSmith + CloudWatch/Grafana | Faster than building |
| Ingestion connectors | **Build** | Depend on in-house ITSM export |
| Commercial "AIOps" platforms | Rejected | Do not read our runbook/incident history semantics; cost; limited guardrail control |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Platform foundation | IaC, VPC, ECS, CI/CD, SSO | MVP |
| WP2 Hosted model + OpenSearch migration | `llm.py` Bedrock, index adapter | MVP |
| WP3 Ingestion connectors | ITSM + reports nightly | MVP |
| WP4 Security and audit | Redaction at ingest, audit to S3, SIEM | MVP |
| WP5 Eval gate + LLMOps | RAGAS strong judge in CI, prompt registry | Phase 2 |
| WP6 Multi-turn + ticket drafting (human approved) | Checkpointer, ticket draft API | Phase 2 |
| WP7 Proactive alerts | Weekly trend digest, anomaly nudges | Target |

| Stage | Architecture | Exit criteria |
|---|---|---|
| Baseline | Local Ollama, Chroma, static keys | - |
| MVP (month 4) | AWS, Bedrock, OpenSearch, SSO, nightly ingest, audit | Pilot KPIs measurable, security sign-off |
| Phase 2 (month 6-9) | Eval gate, prompt registry, multi-turn, ticket drafts | Quality gate in CI, 0 sev guardrail breaches |
| Target (month 12) | Proactive digests, DR tested, cost optimised | SLOs met 3 months |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| ITSM export access | Delay in API credentials | Start with file export (S3 drop) |
| IdP group design | Roles not mapped | Workshop in sprint 1; default deny |
| Bedrock model access/quota | Throttling at month-end | Quota request, retry/backoff, cache |
| Security review | Late findings | Early threat model (OWASP LLM Top 10) |

## Open questions
Does ITSM offer an incremental API? Who owns the monitoring-report format stability?
