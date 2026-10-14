# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
1. Change approved (CAB); eval + safety suite green; staging soak 24 h clean; EHS sign-off if safety files changed.
2. Snapshot RDS and OpenSearch; record index version, prompt hash, policy.yaml version.
3. Run prod CD job (canary 10% / 5 min, then 100%). Deploy outside shift-change windows (A: avoid 05:30-07:00 and 13:30-15:00, 21:30-23:00).
4. Smoke: `/health`; one question per role; zone-denied; safety-blocked; `/metrics`; data freshness within limits.
5. Watch dashboards 30 min; announce to shift leads.

### Go-live checklist
- [ ] SSO groups and zone claims verified (contractor cannot see Z2-Z4)
- [ ] EHS sign-off on safety red-team results (100% refusals)
- [ ] Pen test Critical/High closed
- [ ] Connectors running; freshness alerts armed
- [ ] Policy thresholds approved by Fleet Manager
- [ ] Backup/restore and DR drill done
- [ ] On-call roster for 24x7 sites agreed
- [ ] LLM quota and cost alerts set
- [ ] UAT signed by Fleet Manager and a shift lead

## Release and rollback
Fortnightly releases, hotfix for guardrail issues. Rollback triggers: 5xx > 5% for 5 min; p95 > 30 s for 10 min; any safety-bypass finding; wrong zone data exposure (also Sev1 incident). Rollback = previous ECS task set (<5 min); prompt/model/policy = revert config tag; index = snapshot restore.

## SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability | 99.5% | 2 `/health` failures in 5 min |
| p95 `/ask` | <= 15 s | > 25 s for 10 min warn; > 40 s page |
| 5xx | < 1% | > 5% page |
| Telemetry freshness | <= 15 min | > 1 h page data engineer |
| Event freshness | <= 1 h | > 4 h warn |
| Safety refusals per user | baseline | >= 3/week per user -> EHS |
| Zone-denied rate | baseline | spike -> Security |
| Ungrounded-flag rate | < 5% | > 10% daily -> AI Lead |
| Intent fallback | < 15% | > 25% |
| Thumbs-down | < 15% | > 25% weekly |
| LLM cost/day | < USD 8 | > USD 15 |
Dashboards: service health; data freshness; AI quality; safety and access; cost.

## Support (ITIL)
Incident: Sev1 (outage in a shift, zone leak, safety-bypass advice): 15 min response; Sev2: 1 h. Problem: post-incident review in 5 days. Change: Standard (data refresh), Normal (prompt/model/policy/role), Emergency (guardrail patch). On-call: 24x7 rota shared with DevOps for the pilot (A-05); the robots keep running without the assistant, so Sev1 means harm to safety or data, not production stoppage.

## Phase G - governance
Compliance reviews at M2, M4, GA: ADRs honoured (advisory only, zone scope in all 3 layers, safety guardrails, no direct control path from the assistant to robots). Deviations need ARB waiver plus EHS consent where safety is touched.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Prompt edit | PR + eval report | AI Lead, eval gate | AI Lead |
| Model swap | RFC with quality/cost/latency on golden + safety sets | Eval + security | ARB |
| Policy threshold | Ticket by Fleet Manager | Replay on last 90 days, planted tests | Fleet Manager + EHS informed |
| Role/zone mapping | Ticket | Security | Security |
| Safety guardrail | PR to CODEOWNERS | Red-team rerun | EHS + ARB |
| New robot model/firmware | Notice | Taxonomy and golden-set update | AI Lead |

## Drift and re-evaluation triggers
| Trigger | Action |
|---|---|
| Weekly golden-set drop > 2 pts | Investigate; freeze changes |
| New robot model or firmware rollout | Add events to golden set; check metadata filters |
| New event type > 5 occurrences unmatched | Extend taxonomy and intent examples |
| Rebalancing proposals rejected by leads > 30% for a week | Review BR-2 thresholds |
| Risk-score top-5 never matches actual failures over a quarter | Re-weight (Phase 2/3 learned weights) |
| Provider model change | Full eval before switch |
| Quarterly | Refresh golden set with 20 real faults; 10% judge sample review |

## Open questions
Deployment windows per site; who is on call for OT-side issues.
