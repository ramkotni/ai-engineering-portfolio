# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Workflow, clearance, guardrails, chunking | **Reuse** prototype | 18 tests; classification-first retrieval is the core differentiator |
| QMS vendor's AI search (if offered) | **Evaluate** | May cover text only, not figures; partner clearance model unknown; decision by month 2 |
| Enterprise search (Kendra-class) | Rejected as core | Less control over clearance-before-ranking and image chunks |
| LLM / vision | **Buy** Bedrock | No GPU ops |
| Search | **Buy** OpenSearch managed | HA, hybrid |
| DMS connector | **Build** | System-specific |
| Validation toolkit | **Buy/reuse** QA's CSV tooling | Evidence management exists |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Foundation | IaC, CI/CD, SSO, partner federation design | MVP |
| WP2 Hosted models | Bedrock text + vision; caption eval | MVP |
| WP3 DMS/ERP connectors with versions + classification | MVP |
| WP4 Security | Partner edge, red-team, object-lock audit | MVP |
| WP5 Validation | CSV plan, risk assessment, test evidence, release baseline | MVP -> GA |
| WP6 Eval gate + prompt registry | CI gate, `qa/v2` experiments | Phase 2 |
| WP7 Supersede/effective-date handling and inspection mode (query "as of" a date) | Phase 2 |
| WP8 Caption human-review queue for GxP-critical figures | Phase 2 |
| WP9 Multilingual documents | Target |

| Stage | Architecture | Exit |
|---|---|---|
| Baseline | Local Ollama, 5 files | - |
| MVP (month 5) | AWS, DMS sync, SSO, internal users only | QA acceptance |
| Phase 1 GA (month 8) | Validated release incl. partners | Validation report signed |
| Phase 2 (month 11-14) | Eval gate, as-of queries, caption review | KPIs |
| Target | Multilingual, broader doc types | - |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| DMS API / metadata quality | Missing classification | Fail closed (confidential), report to content steward |
| Partner IdP | Provisioning delays | Invite-based accounts first |
| Validation capacity | QA bandwidth | Early CSV lead, automated evidence |
| Bedrock vision quality | Caption errors | Eval on 100 figures before MVP; human review for critical figures |

## Open questions
Does the QMS vendor roadmap include a native assistant? Who signs the validation summary?
