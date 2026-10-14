# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
1. Change record approved; validation evidence filed; eval gate and staging soak green.
2. Snapshot OpenSearch; record prompt versions, model IDs, index alias, config hash.
3. Build the new index in parallel; run retrieval and partner-leak probes against it; switch alias.
4. Run prod CD (canary 10% / 10 min -> 100%).
5. Smoke: one question per role; partner leakage probe (restricted chunks = 0); `/images` 403 probe; `/metrics`; ingestion queue healthy.
6. Watch dashboards 30 min; publish release note; close change record.

### Go-live checklist
- [ ] Validation summary report signed by QA
- [ ] Classification mapping verified on 100 sampled documents
- [ ] Partner red-team passed (0 leakage); pen test Critical/High closed
- [ ] SSO and partner federation tested; deprovisioning tested
- [ ] Audit bucket object lock active; retention set
- [ ] Ingestion exceptions report reviewed by content steward
- [ ] Caption eval >= 95%; figure label approved
- [ ] On-call, alerts and runbooks in place; DR drill done
- [ ] Cost alerts; Bedrock quotas confirmed

## Release and rollback
Monthly releases (validated baseline), hotfix via emergency change. Rollback triggers: any partner restricted-chunk count > 0 (Sev1), 5xx > 5% for 5 min, p95 > 40 s for 10 min, ingestion producing wrong classifications. Rollback = previous ECS task set and previous index alias (kept for 7 days); prompt/model rollback = revert config tag with a change record.

## SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability | 99.5% business hours | 2 failed probes in 5 min |
| p95 `/ask` | <= 20 s | > 30 s 10 min warn; > 45 s page |
| 5xx | < 1% | > 5% page |
| **Partner restricted chunks** | 0 | any -> page Security, auto rollback |
| Index freshness | new/superseded doc visible <= 2 h | > 6 h warn |
| Ingestion DLQ | 0 stuck | any > 24 h |
| Quarantined docs | trend down | > 20 open |
| Ungrounded flag rate | < 5% | > 10% daily |
| "Not covered" rate | baseline | spike -> content gap review |
| Caption failure rate | < 2% | > 5% |
| LLM cost/day | < USD 15 | > USD 25 |
Dashboards: service; ingestion and freshness; AI quality; access and security; cost.

## Support (ITIL)
Incident: Sev1 (partner leakage, wrong classification exposure, outage during an excursion) 15 min; Sev2 1 h. Problem: review in 5 days; recurring extraction failures per document type tracked as problems. Change: Standard (document sync), Normal (prompt/model/classification mapping/role), Emergency (guardrail patch). Changes to the validated system follow the QMS change-control SOP with impact assessment by QA. On-call: business-hours L2 (A-05), Sev1 paging out of hours for partner-leak alarms.

## Phase G - governance
Compliance reviews at M2, M5 (before validation execution) and GA: clearance-before-retrieval honoured on all endpoints; no write path to the DMS; audit immutability; pinned models. Deviations: ARB waiver + QA concurrence.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Prompt version | PR + change record + eval report | AI Lead; QA impact assessment (risk-based re-test scope) | AI Lead + QA |
| Model swap (text/vision) | RFC with golden + caption eval | Eval + security | ARB + QA |
| Classification mapping | Ticket by RA/Security | Sample verification (100 docs) | Security + RA |
| New document source | Request by data owner | Quality and privacy review | Data owner + Security |
| Architecture change | ADR | ARB | ARB |
| Role/clearance change | Ticket | Security | Security |

## Drift and re-evaluation triggers
| Trigger | Action |
|---|---|
| Weekly golden-set drop > 2 pts | Investigate, freeze changes |
| New document type or template (e.g. new SOP layout) | Re-run extraction tests; add to golden set |
| Table/figure extraction failure rate > 3% | Fix loader; re-index affected docs |
| Provider changes vision/text model version | Full eval incl. caption set before switch |
| "Not covered" rate doubles | Content gap review with document owners |
| Corpus grows 2x | Re-run retrieval sweep (mode x k; consider k=10) |
| Quarterly | Refresh golden set with 20 real questions; 10% judge sample human review by QA |

## Open questions
Out-of-hours support for excursions; whether the QMS requires periodic review of the validated state (annual?).
