# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Extraction pipeline, section agents, guardrails, clearance | **Reuse** prototype | 37 tests; extraction contract tests |
| Commercial pipeline-intelligence platforms (trial/deal databases) | **Evaluate, complement** | Better data coverage for companies and deals; no cross-reading of our internal strategy brief; could become an additional structured source if licensed |
| Generic "chat with PDF" tools | Rejected | Fail on two-column layout, cross-page tables, figures, clearance, fixed briefing structure |
| LLM / vision | **Buy** Bedrock | No GPU ops |
| Search | **Buy** OpenSearch | Hybrid, HA |
| Document intelligence service (Textract-class) | **Evaluate as fallback** | Scanned PDFs only |
| ClinicalTrials.gov | **Reuse** public API | Free, structured |
| Content licences | **Buy** as required | Legal gate |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Foundation | IaC, CI/CD, SSO | MVP |
| WP2 Hosted models + managed index | Bedrock text/vision, OpenSearch | MVP |
| WP3 Content licensing and rights register | Legal review per source; ingestion gate | MVP |
| WP4 Ingestion at scale | Sync, quarantine, extraction checks on 30 real documents | MVP |
| WP5 Clinical review workflow | Reviewer sign-off recorded with briefing version | MVP |
| WP6 Eval gate | Real-document extraction set; RAGAS with strong judge | Phase 2 start |
| WP7 Export (slides/Word), watchlists, scheduled refresh and change alerts | Phase 2 |
| WP8 Scanned PDFs (OCR), more conditions and registries (EU CTIS) | Target |

| Stage | Architecture | Exit |
|---|---|---|
| Baseline | Local Ollama, 4 synthetic files | - |
| MVP (month 3) | AWS, SSO, licensed sample, one service line (cardiometabolic) | Legal + clinical sign-off, pilot |
| Phase 2 (month 5-8) | Eval gate, export, refresh | Prep-time KPI |
| Target (month 12) | Watchlists, alerts, more registries | - |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| Licences for guideline PDFs | Not permitted for AI processing | Early Legal review; fall back to open-access guidelines and metadata-only indexing |
| Real PDFs with unseen layouts | Extraction failures | 30-document extraction acceptance set; Textract fallback; extraction viewer |
| ClinicalTrials.gov API changes | Breaking schema | Adapter with contract tests; cached snapshots |
| Clinical reviewer availability | Bottleneck | Sampled review policy; asynchronous review |

## Open questions
Which licensed sources come first? Is a commercial pipeline database already available to the team?
