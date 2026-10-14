# 05 - Phase E: Opportunities & Solutions

## Build vs buy vs reuse
| Component | Decision | Why |
|---|---|---|
| Scoring pipeline, validation/cleaning, feature builder, drift | **Reuse** prototype | Tested (11 tests); small and understandable |
| PPM vendor "predictive" add-on | **Evaluate** | Often opaque, tuned to vendor data; our own history and thresholds matter more; compare AUC on our data before deciding |
| AutoML platform | Rejected | Interpretability and the selection rule are requirements; AutoML adds cost with +/-0.02 AUC gains |
| Registry | **Buy/reuse** MLflow or SageMaker | Standard capability |
| LLM advisor | **Buy** Bedrock | Small volume |
| Warehouse feed | **Build** | PPM-specific |

## Work packages and transition architectures
| WP | Content | Stage |
|---|---|---|
| WP1 Data foundation | PPM extract, data contract, warehouse tables, validation in pipeline | MVP |
| WP2 Training pipeline + registry | Scheduled/triggered, model card, comparison to production | MVP |
| WP3 Serving + SSO | API, UI, roles, audit | MVP |
| WP4 Monitoring | PSI, calibration, subgroup metrics, alerts | MVP |
| WP5 Shadow mode | Score all intake proposals for 3 months without showing to board; compare with decisions/outcomes | MVP -> Phase 2 gate |
| WP6 Advisor in production | Bedrock, playbook governance | Phase 2 |
| WP7 Outcome feedback and scheduled retrain | Matured outcomes, gated promotion | Phase 2 |
| WP8 What-if and portfolio view | Sensitivity of score to input changes; budget-constrained portfolio | Target |

| Stage | Architecture | Exit |
|---|---|---|
| Baseline | Local, synthetic | - |
| MVP (month 3) | AWS, pipeline, registry, serving, shadow mode | Model Risk validation passed |
| Phase 2 (month 5-8) | Board-visible scores, advisor, outcome loop | Calibration on real outcomes OK |
| Target (month 12) | What-if, portfolio view | KPIs |

## Dependencies and integration risks
| Dependency | Risk | Mitigation |
|---|---|---|
| Historical data quality and labels | Few labelled projects, inconsistent success definition | Label workshop; validation report; start shadow mode |
| PPM access | Delay | CSV export |
| Model Risk capacity | Slow validation | Early engagement, standard template (model card) |
| Selection bias | Optimistic performance | Time-based hold-out; note in model card |

## Open questions
Will the PMO accept shadow mode for a quarter before using scores in decisions?
