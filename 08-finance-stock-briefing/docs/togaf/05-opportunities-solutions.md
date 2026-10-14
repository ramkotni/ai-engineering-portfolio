# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Workflow, EDGAR parser, metrics, compliance filter, roles | **Reuse** prototype | 31 tests; handles real 8.5 MB 10-K; compliance filter 5/5 and 4/4 |
| Terminal/research vendor AI assistants | **Evaluate in parallel** | May bring richer data, but often lack the firm's lexicon, role scoping, archive hooks; decision by month 2 |
| Financial-data summary APIs | Rejected as core | Unknown provenance; cannot enforce lexicon or ticker-scoped RAG |
| Market data | **Buy** licensed vendor | Terms, quality, entitlements |
| LLM / embeddings | **Buy** Bedrock | No GPU ops |
| Search | **Buy** OpenSearch | HA |
| Archive | **Buy/reuse** firm archive or S3 Object Lock | Regulatory |
| Surveillance integration | **Build** thin export | Vendor-specific |
| Lexicon | **Build** with Compliance | Firm-specific |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Foundation | IaC, CI/CD, SSO, network allow-lists | MVP |
| WP2 Licensed market data adapter + entitlements | MVP |
| WP3 Hosted models + managed index; EDGAR shared cache and rate limiter | MVP |
| WP4 Compliance package | Lexicon, refusal wording, disclaimer, red-team set, supervisory procedure update | MVP |
| WP5 WORM archive + audit + `GET /audit` UI for compliance | MVP |
| WP6 Pilot with 40 advisors | MVP -> GA |
| WP7 Eval gate + prompt registry | Phase 2 |
| WP8 CRM context (read-only), watchlists, earnings-call transcripts | Phase 2 |
| WP9 Non-US filings, additional document types | Target |

| Stage | Architecture | Exit |
|---|---|---|
| Baseline | Local Ollama; Yahoo; JSONL audit | - |
| MVP (month 3) | AWS, licensed data, archive, SSO | Compliance sign-off, pilot start |
| GA (month 5) | All advisors | KPIs |
| Phase 2 (month 8-10) | Eval gate, CRM context, watchlists | Adoption |
| Target (month 12+) | Non-US, transcripts | - |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| Market-data vendor contract | Procurement delay | Delayed-data entitlement first; synthetic mode available |
| Compliance review capacity | Lexicon iterations | Weekly review slots; start in sprint 1 |
| EDGAR availability/limits | Throttling | Shared cache, pre-warming, backoff |
| Archive platform decision | Rework | S3 Object Lock as default; export interface |
| Pre-market load | Latency | Pre-warm index, autoscale, cache |

## Open questions
Which vendor? Is there an existing archive/surveillance platform to integrate?
