# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Router, retrieval, guardrails, graph | **Reuse** prototype | 48 unit + 3 integration tests; plant-specific safety rules |
| Enterprise search / Copilot over SharePoint | **Evaluate, not adopt as core** | No safety-first routing, numeric grounding or emergency banner; unclear table handling; use as a benchmark |
| CMMS vendor assistant | **Evaluate** | May answer asset questions but not safety or quality sources |
| LLM + embeddings | **Buy** Bedrock | No GPU ops; guardrails managed |
| Vector search | **Buy** OpenSearch | HA |
| Document sync | **Build** | System-specific |
| Mobile device layer | **Reuse** corporate MDM | - |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Foundation | IaC, CI/CD, SSO with plant roles | MVP |
| WP2 Hosted models + managed index | Bedrock + Guardrails, OpenSearch | MVP |
| WP3 Document-control sync with revisions | MVP |
| WP4 Safety validation | EHS red-team set (100+ cases), emergency drills, sign-off | MVP |
| WP5 Tablet UX and shift pilot | One shift, then three | MVP -> GA |
| WP6 Eval gate + prompt registry | CI gate | Phase 2 |
| WP7 Multi-turn (checkpointer), OCR/vision for scans and diagrams | Phase 2 |
| WP8 CMMS asset context (read-only), multi-plant, languages | Target |

| Stage | Architecture | Exit |
|---|---|---|
| Baseline | Local Ollama, 13 documents | - |
| MVP (month 4) | AWS, sync, SSO, one plant | EHS sign-off, shift pilot |
| Phase 2 (month 6-9) | Eval gate, multi-turn, scanned docs | KPIs |
| Target (month 12+) | CMMS context, 2nd plant, languages | Rollout plan |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| Controlled-document metadata | Missing revision/owner | Quarantine; owners fix |
| EHS capacity | Review bottleneck | Pre-agreed red-team set; scheduled sessions |
| Plant connectivity | Wi-Fi dead zones | Test coverage; verbatim offline fallback (Phase 2) |
| Bedrock quotas at shift start | Throttling | Quota request, backoff, cache, queueing UI message |

## Open questions
Plant selection for MVP; is there an MDM policy for tablets used by contractors?
