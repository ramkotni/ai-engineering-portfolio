# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Agents, analytics, guardrails, zone RBAC | **Reuse** prototype | 25 tests; domain rules encoded |
| Fleet vendor's analytics module | **Evaluate, not adopt** | Typically fault-code oriented, no cross-source RCA, no custom policy; revisit if included in licence |
| LLM | **Buy** Bedrock | No GPU ops |
| Search / tables | **Buy** managed | HA |
| Connectors | **Build** | Site-specific console and CMMS |
| Predictive-maintenance ML platform | Defer | Rule-based risk score first; learn from outcomes in Phase 2 |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Foundation | IaC, CI/CD, SSO with zone claim | MVP |
| WP2 Hosted model + managed index | Bedrock, OpenSearch, RDS | MVP |
| WP3 Connectors | Fleet console events/telemetry, CMMS | MVP |
| WP4 Safety and security | Red-team set with EHS, audit to SIEM | MVP |
| WP5 Eval gate + prompt registry | CI gate | Phase 2 |
| WP6 Proposal approval flow | Lead approves task moves; export to console (still human-executed) | Phase 2 |
| WP7 Learned risk weights | Train from outcome data (supervised), compare to rule score | Target |
| WP8 Stream-based freshness | Near-real-time events | Target |

| Stage | Architecture | Exit |
|---|---|---|
| Baseline | Local, static CSV | - |
| MVP (month 4) | AWS, scheduled ingest, SSO, zones | Pilot on 1 shift |
| Phase 2 (month 6-9) | Eval gate, approvals, all shifts | Safety red-team 100% |
| Target (month 12) | Learned weights, live events | Downtime KPI reached |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| Fleet console API | Rate limits, no history API | Daily export fallback |
| CMMS access | Slow approvals | CSV export first |
| EHS review | Late veto on wording | Early involvement, review red-team set |
| Site network | VPN lead time | Start request in sprint 1 |

## Open questions
Does the fleet vendor allow API read access under the support contract?
