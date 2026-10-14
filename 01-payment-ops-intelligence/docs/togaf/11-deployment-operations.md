# 11 - Deployment, Operations, Phases G and H

## Deployment runbook (prod)
1. Confirm change ticket approved (CAB), eval gate green, staging soak 24 h clean.
2. Freeze ingestion; snapshot OpenSearch; record `index_version` and prompt hash.
3. Run CD prod job -> canary 10% for 5 min, then 100%.
4. Smoke: `/health`, one `/ask` per role, denied case, blocked case, `/metrics` scrape.
5. Watch dashboards 30 min; unfreeze ingestion.
6. Announce release notes; record in change log.

### Go-live checklist
- [ ] SSO groups mapped, default deny verified
- [ ] Pen test findings closed (Critical/High)
- [ ] Guardrail red-team 100% blocked
- [ ] Audit log delivering to S3 and SIEM
- [ ] Alerts routed to on-call; runbooks linked
- [ ] Backup/restore tested; DR drill done
- [ ] Cost alerts configured; LLM quota confirmed
- [ ] UAT signed by Ops Manager; compliance sign-off

## Release and rollback
Release train: fortnightly; hotfix on demand. Rollback triggers: 5xx > 5% for 5 min, p95 > 40 s for 10 min, any guardrail-bypass finding. Rollback = CodeDeploy reverts to previous task set (< 5 min); prompt/model rollback = revert config tag; index rollback = restore snapshot.

## Monitoring, SLOs and alerts
| SLI | SLO | Alert |
|---|---|---|
| Availability (`/health`) | 99.5% business hours | 2 failures / 5 min page |
| p95 `/ask` latency | <= 20 s | > 30 s for 10 min warn; > 40 s page |
| Error rate (5xx) | < 1% | > 5% page |
| Guardrail block rate | baseline +/- 3 sigma | spike -> security review |
| Output-guardrail flag rate (ungrounded) | < 5% | > 10% daily -> AI Lead |
| Intent fallback rate | < 10% | > 20% |
| Thumbs-down ratio | < 15% | > 25% weekly |
| LLM cost/day | < USD 15 | > USD 25 |
Dashboards: Service health; AI quality (flags, fallbacks, feedback); Cost & tokens; Security (blocks, denials by role).

## Support model (ITIL-aligned)
| Process | Practice |
|---|---|
| Incident | Sev1 (outage or guardrail breach): 15 min response, on-call AI/DevOps pair; Sev2: 1 h; comms to Ops Manager |
| Problem | Post-incident review within 5 days; recurring flag/fallback causes tracked as problems |
| Change | Standard (data refresh), Normal (prompt/model/role change, CAB + ARB), Emergency (guardrail patch) |
| On-call | Business-hours L2, out-of-hours best effort for pilot (A-06) |

## Phase G - implementation governance
Architecture compliance review at M2 (staging), M4 (pilot) and before GA: check ADRs are honoured (read-only, RBAC, grounding, no unmanaged data egress). Deviations require ARB waiver recorded in 12.

## Phase H - change management
| Change | Request | Assessment | Approval |
|---|---|---|---|
| Prompt edit | PR with diff + eval report | AI Lead + eval gate | AI Lead; ARB informed |
| Model swap | RFC with cost/quality/latency comparison on golden sets | Eval + security review | ARB |
| Role/permission change | Ticket by Ops Manager | Security | Security + Internal Audit informed |
| Architecture change | ADR draft | ARB | ARB |
| New data source | Data-owner request | Classification + privacy review | Data owner + Security |

## Drift monitoring and retraining/re-evaluation triggers
No model is trained; "retraining" means re-evaluation, re-indexing and prompt tuning.
| Trigger | Action |
|---|---|
| Weekly golden-set run drops > 2 pts on any metric | Investigate; freeze prompt changes |
| New failure category appears in > 5 incidents without matching category | Update taxonomy, intent examples, golden set |
| Provider announces model deprecation / version change | Re-run full eval before switch |
| Fallback or ungrounded-flag rate doubles | Review retrieval and prompts |
| Corpus grows 2x | Re-run retrieval sweep (mode x k) |
| Quarterly | Refresh golden set with 20 real tickets; human review of 10% judged sample |

## Open questions
Out-of-hours support expectation; whether CAB treats prompt changes as Normal or Standard.
