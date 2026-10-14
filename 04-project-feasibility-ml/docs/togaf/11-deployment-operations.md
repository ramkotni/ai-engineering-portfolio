# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
**Application release**
1. Change approved; CI gates green; staging smoke passed.
2. Deploy via CD (canary 10% / 5 min -> 100%).
3. Smoke: `/health`; one `/predict` per role; 422 on invalid input; `/drift`; `/metrics`; a determinism check (known input gives known probability for the current model version).

**Model promotion**
1. Candidate registered with model card; automated gates green; shadow results reviewed.
2. Model Risk approval recorded (approver role in the registry).
3. Move alias `production`; serving reloads; confirm model version in `/model` and a canary prediction.
4. Keep previous version 90 days; rollback = move alias back.

### Go-live checklist (first production use)
- [ ] Independent validation report signed by Model Risk
- [ ] Label definition and selection-bias note in the model card
- [ ] Subgroup (type, region) metrics reviewed and accepted
- [ ] Shadow-mode comparison of >= 3 months reviewed with the PMO
- [ ] Decision threshold approved by Portfolio Director
- [ ] SSO, roles and audit verified; viewer limits tested
- [ ] PSI and calibration jobs scheduled; alerts routed
- [ ] DR drill done; registry backup tested
- [ ] Advisor playbook approved by PMO; advisor flag on only if approved
- [ ] Board communication: "decision support only"

## Release and rollback
Application: fortnightly; model: on trigger, not before a month of data unless drift is significant. Rollback triggers: 5xx > 5% for 5 min; p95 `/predict` > 1 s for 10 min; unexpected score shift (mean probability moves > 0.1 week over week without input drift); any fairness-gate failure found after promotion. Rollback = previous task set or previous registry alias.

## SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability | 99.5% business hours | 2 failed probes / 5 min |
| `/predict` p95 | <= 300 ms | > 1 s for 10 min |
| `/advise` p95 | <= 20 s | > 40 s |
| 5xx | < 1% | > 5% page |
| Data drift PSI | < 0.1 (stable) | >= 0.1 warn; >= 0.25 page model owner |
| OOD rate | < 5% of predictions | > 15% weekly |
| Brier on matured outcomes | <= 0.18 | > 0.18 ticket |
| Subgroup AUC gap | <= 0.05 | > 0.05 ticket to Model Risk |
| Advisor grounding violations shown | 0 | any |
| Advisor cost | < USD 20/month | > USD 50 |
Dashboards: service; model health (PSI, calibration, score distribution, band mix); fairness; advisor quality and cost.

## Support (ITIL)
Incident: Sev1 (wrong model served, score outage during a board cycle, data exposure): 30 min response in business hours; Sev2: 4 h. Problem: score anomalies and repeated drift alerts reviewed monthly. Change: Standard (data refresh, retrain with unchanged config), Normal (feature, threshold, role, prompt/playbook, app release), Emergency (rollback). On-call: business-hours only (A-05); the board calendar defines high-attention weeks.

## Phase G - governance
Compliance reviews at MVP, before shadow end, and at GA: interpretable model retained (any non-LR selection above +0.02 AUC needs ARB review), no protected attributes, human decision preserved, audit complete, model card complete.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Retrain, same config | Pipeline trigger | Gates + shadow | Model owner; Model Risk approves promotion |
| New feature or model family | RFC | Interpretability, leakage, fairness | ARB + Model Risk |
| Threshold | Ticket by Director | Replay on last 12 months (precision/recall trade-off) | Portfolio Director; Compliance informed |
| Playbook edit | PR by PMO | Advisor regression set | PMO owner + AI Lead |
| Advisor prompt/model | PR/RFC | Advisor eval | AI Lead |
| Role change | Ticket | Security | Security |

## Drift and retraining triggers
| Trigger | Action |
|---|---|
| PSI >= 0.25 on any feature (or >= 0.1 on 3+) | Investigate; retrain candidate; shadow compare |
| Brier > 0.18 or calibration slope outside 0.9-1.1 on >= 30 matured outcomes | Recalibrate or retrain |
| AUC on matured outcomes drops > 0.05 vs validation | Retrain; review features and label |
| Portfolio mix change (e.g. > 20% new project type) | Retrain with new type; check OOD rate |
| Process change (e.g. new stage gates) | Review label definition |
| Quarterly | Scheduled retrain on all matured outcomes; compare to production |
| Advisor: playbook change or LLM version change | Advisor regression set |

## Open questions
Maturity period for outcomes; on-call needs for the board cycle.
